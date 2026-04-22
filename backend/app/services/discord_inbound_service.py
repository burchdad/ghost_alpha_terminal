from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

try:
    from nacl.exceptions import BadSignatureError
    from nacl.signing import VerifyKey
except Exception:  # pragma: no cover
    BadSignatureError = Exception
    VerifyKey = None

from app.core.config import settings
from app.db.models import DiscordInboundEvent
from app.db.session import get_session


@dataclass
class DiscordEventIngestResult:
    accepted: bool
    event_type: str
    stored_id: int | None
    extracted_symbols: list[str]


class DiscordInboundService:
    SYMBOL_PATTERN = re.compile(r"\b[A-Z]{1,6}\b")

    def is_enabled(self) -> bool:
        return bool(settings.discord_inbound_enabled)

    def has_public_key(self) -> bool:
        return bool(str(settings.discord_public_key or "").strip())

    def verify_signature(self, *, signature_hex: str, timestamp: str, raw_body: bytes) -> bool:
        key_hex = str(settings.discord_public_key or "").strip()
        if not key_hex or VerifyKey is None:
            return False

        try:
            verify_key = VerifyKey(bytes.fromhex(key_hex))
            message = timestamp.encode("utf-8") + raw_body
            verify_key.verify(message, bytes.fromhex(signature_hex))
            return True
        except (ValueError, BadSignatureError):
            return False

    def _extract_symbols(self, text: str) -> list[str]:
        if not text:
            return []
        blocked = {"THE", "THIS", "THAT", "WITH", "FROM", "ALERT", "LONG", "SHORT", "CALL", "PUT"}
        symbols = [token for token in self.SYMBOL_PATTERN.findall(text.upper()) if token not in blocked]
        deduped: list[str] = []
        for sym in symbols:
            if sym not in deduped:
                deduped.append(sym)
        return deduped[:20]

    def ingest_payload(self, payload: dict[str, Any]) -> DiscordEventIngestResult:
        event_type = str(payload.get("type") or payload.get("event", {}).get("type") or "unknown")
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        content = str(data.get("content") or payload.get("content") or "")
        channel_id = str(payload.get("channel_id") or data.get("channel_id") or "") or None

        symbols = self._extract_symbols(content)

        with get_session() as session:
            row = DiscordInboundEvent(
                event_type=event_type,
                application_id=str(payload.get("application_id") or "") or None,
                guild_id=str(payload.get("guild_id") or data.get("guild_id") or "") or None,
                channel_id=channel_id,
                author_id=str((data.get("author") or {}).get("id") if isinstance(data.get("author"), dict) else "") or None,
                content=content or None,
                extracted_symbols=json.dumps(symbols),
                payload_json=json.dumps(payload),
                created_at=datetime.now(tz=timezone.utc),
            )
            session.add(row)
            session.flush()
            stored_id = int(row.id)

        self._auto_inject_to_signal_service(symbols, channel_id)

        return DiscordEventIngestResult(
            accepted=True,
            event_type=event_type,
            stored_id=stored_id,
            extracted_symbols=symbols,
        )

    def _auto_inject_to_signal_service(self, symbols: list[str], channel_id: str | None) -> None:
        """Push extracted symbols into the live signal watchlist cache."""
        try:
            from app.services.discord_signal_service import discord_signal_service  # noqa: PLC0415 (lazy import)
            if not discord_signal_service.is_enabled():
                return
            allowed = discord_signal_service._allowed_channels()
            if allowed and (channel_id or "") not in allowed:
                return
            discord_signal_service.invalidate_cache()
        except Exception:
            pass


# Singleton
discord_inbound_service = DiscordInboundService()
