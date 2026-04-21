from __future__ import annotations

import logging
import time
from threading import Lock
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings


logger = logging.getLogger(__name__)


class DiscordNotifierService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._last_sent_monotonic: float | None = None
        self._last_sent_by_severity: dict[str, float] = {}
        self._last_sent_by_signature: dict[str, float] = {}

    def _is_configured(self) -> bool:
        webhook = str(settings.discord_webhook_url or "").strip()
        return bool(settings.discord_alerts_enabled and webhook)

    def _cooldown_seconds(self) -> int:
        return max(0, int(settings.discord_min_interval_seconds or 600))

    def _critical_cooldown_seconds(self) -> int:
        return max(0, int(settings.discord_critical_min_interval_seconds or 30))

    def _dedupe_window_seconds(self) -> int:
        return max(0, int(settings.discord_dedupe_window_seconds or 120))

    @staticmethod
    def _message_signature(*, title: str, message: str, severity: str, context: dict[str, Any] | None) -> str:
        context_str = ""
        if context:
            pairs = sorted((str(k), str(v)) for k, v in context.items())
            context_str = "|".join(f"{k}={v}" for k, v in pairs)
        return f"{severity}|{title}|{message}|{context_str}".strip().lower()

    def _seconds_until_next_send(self) -> int:
        cooldown = self._cooldown_seconds()
        if cooldown <= 0:
            return 0
        with self._lock:
            if self._last_sent_monotonic is None:
                return 0
            elapsed = time.monotonic() - self._last_sent_monotonic
        return max(0, int(cooldown - elapsed))

    def _seconds_until_next_send_for_severity(self, *, severity: str) -> int:
        severity = severity.strip().lower()
        cooldown = self._critical_cooldown_seconds() if severity == "critical" else self._cooldown_seconds()
        if cooldown <= 0:
            return 0
        with self._lock:
            last = self._last_sent_by_severity.get(severity)
        if last is None:
            return 0
        elapsed = time.monotonic() - last
        return max(0, int(cooldown - elapsed))

    def _is_duplicate_in_window(self, *, signature: str) -> bool:
        window = self._dedupe_window_seconds()
        if window <= 0:
            return False
        now = time.monotonic()
        with self._lock:
            # prune old keys opportunistically
            stale_keys = [k for k, t in self._last_sent_by_signature.items() if (now - t) > window]
            for key in stale_keys:
                self._last_sent_by_signature.pop(key, None)

            previous = self._last_sent_by_signature.get(signature)
            if previous is not None and (now - previous) <= window:
                return True
        return False

    def _can_send(self, *, severity: str) -> bool:
        return self._seconds_until_next_send_for_severity(severity=severity) <= 0

    def _mark_sent(self, *, severity: str, signature: str) -> None:
        severity = severity.strip().lower()
        now = time.monotonic()
        with self._lock:
            self._last_sent_monotonic = now
            self._last_sent_by_severity[severity] = now
            self._last_sent_by_signature[signature] = now

    def status(self) -> dict[str, Any]:
        seconds_until_next = self._seconds_until_next_send()
        return {
            "enabled": bool(settings.discord_alerts_enabled),
            "configured": self._is_configured(),
            "webhook_present": bool(str(settings.discord_webhook_url or "").strip()),
            "username": str(settings.discord_username or "Ghost Alpha Ops"),
            "cooldown_seconds": self._cooldown_seconds(),
            "critical_cooldown_seconds": self._critical_cooldown_seconds(),
            "dedupe_window_seconds": self._dedupe_window_seconds(),
            "seconds_until_next_send": seconds_until_next,
            "can_send_now": seconds_until_next <= 0,
        }

    def send_message(
        self,
        *,
        title: str,
        message: str,
        severity: str = "info",
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Post a structured alert message to Discord webhook.

        Returns False when integration is disabled/unconfigured or when delivery fails.
        """
        if not self._is_configured():
            return False

        severity_normalized = severity.strip().lower()
        signature = self._message_signature(
            title=title,
            message=message,
            severity=severity_normalized,
            context=context,
        )

        if self._is_duplicate_in_window(signature=signature):
            logger.info(
                "discord_webhook_suppressed reason=duplicate_in_window window_seconds=%s severity=%s",
                self._dedupe_window_seconds(),
                severity_normalized,
            )
            return False

        if not self._can_send(severity=severity_normalized):
            logger.info(
                "discord_webhook_suppressed cooldown_seconds=%s seconds_until_next=%s severity=%s",
                self._critical_cooldown_seconds() if severity_normalized == "critical" else self._cooldown_seconds(),
                self._seconds_until_next_send_for_severity(severity=severity_normalized),
                severity_normalized,
            )
            return False

        color_map = {
            "info": 0x3B82F6,
            "warning": 0xF59E0B,
            "critical": 0xEF4444,
            "success": 0x10B981,
        }
        embed_color = color_map.get(severity_normalized, color_map["info"])

        fields = []
        if context:
            for key, value in context.items():
                fields.append(
                    {
                        "name": str(key).replace("_", " ").title(),
                        "value": str(value),
                        "inline": True,
                    }
                )

        payload: dict[str, Any] = {
            "username": str(settings.discord_username or "Ghost Alpha Ops"),
            "embeds": [
                {
                    "title": title,
                    "description": message,
                    "color": embed_color,
                    "timestamp": datetime.now(tz=timezone.utc).isoformat(),
                    "fields": fields[:10],
                }
            ],
        }

        try:
            with httpx.Client(timeout=max(1.0, float(settings.discord_timeout_seconds or 5.0))) as client:
                response = client.post(str(settings.discord_webhook_url).strip(), json=payload)
                if response.status_code >= 400:
                    logger.error(
                        "discord_webhook_post_failed status=%s body=%s",
                        response.status_code,
                        response.text[:400],
                    )
                    return False
            self._mark_sent(severity=severity_normalized, signature=signature)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("discord_webhook_exception error=%s", exc)
            return False


# Singleton service
discord_notifier = DiscordNotifierService()
