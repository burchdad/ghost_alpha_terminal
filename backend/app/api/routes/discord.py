from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Path, Request, status
from pydantic import BaseModel, Field

from app.api.deps.auth import CurrentUser, HighTrustUser
from app.core.config import settings
from app.db.models import User
from app.services.discord_inbound_service import discord_inbound_service
from app.services.discord_notifier import discord_notifier
from app.services.discord_signal_service import discord_signal_service


router = APIRouter(prefix="/discord", tags=["discord"])


class DiscordOutboundRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    severity: str = Field(default="info", min_length=1, max_length=32)


class PinSymbolRequest(BaseModel):
    asset_class: str = Field(default="equity", min_length=1, max_length=16)
    note: str | None = Field(default=None, max_length=256)


@router.get("/outbound/status", summary="Discord outbound webhook status")
async def discord_outbound_status(user: User = CurrentUser) -> dict:
    _ = user
    return discord_notifier.status()


@router.post("/outbound/test", summary="Send outbound Discord test alert")
async def discord_outbound_test(user: User = HighTrustUser) -> dict:
    delivered = discord_notifier.send_message(
        title="Ghost Alpha Discord Test",
        message="Ghost Alpha outbound test",
        severity="info",
        context={
            "triggered_by": str(user.email),
            "environment": str(settings.app_env),
        },
    )
    return {
        "ok": True,
        "delivered": delivered,
        "status": discord_notifier.status(),
    }


@router.post("/outbound/send", summary="Send outbound Discord alert")
async def discord_outbound_send(payload: DiscordOutboundRequest, user: User = HighTrustUser) -> dict:
    delivered = discord_notifier.send_message(
        title="Ghost Alpha Alert",
        message=payload.message,
        severity=payload.severity,
        context={
            "triggered_by": str(user.email),
            "environment": str(settings.app_env),
        },
    )
    return {
        "ok": True,
        "delivered": delivered,
        "status": discord_notifier.status(),
    }


@router.get("/inbound/status", summary="Discord inbound webhook status")
async def discord_inbound_status(user: User = CurrentUser) -> dict:
    _ = user
    return {
        "enabled": discord_inbound_service.is_enabled(),
        "public_key_configured": discord_inbound_service.has_public_key(),
    }


@router.post("/inbound/events", summary="Discord inbound event webhook receiver")
async def discord_inbound_events(
    request: Request,
    x_signature_ed25519: str | None = Header(default=None),
    x_signature_timestamp: str | None = Header(default=None),
) -> dict:
    if not discord_inbound_service.is_enabled():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Discord inbound webhook is disabled")

    raw_body = await request.body()
    max_bytes = max(1, int(settings.discord_inbound_max_body_kb or 64)) * 1024
    if len(raw_body) > max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="Payload too large")

    if not x_signature_ed25519 or not x_signature_timestamp:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing Discord signature headers")

    if not discord_inbound_service.verify_signature(
        signature_hex=x_signature_ed25519,
        timestamp=x_signature_timestamp,
        raw_body=raw_body,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid Discord signature")

    payload = await request.json()

    # Discord interaction ping handshake support.
    if payload.get("type") == 1:
        return {"type": 1}

    result = discord_inbound_service.ingest_payload(payload)
    return {
        "ok": True,
        "accepted": result.accepted,
        "event_type": result.event_type,
        "stored_id": result.stored_id,
        "symbols": result.extracted_symbols,
    }


# ---------------------------------------------------------------------------
# Signal watchlist management
# ---------------------------------------------------------------------------

@router.get("/signals/status", summary="Discord signal service status and active snapshot")
def get_signal_status(user: User = CurrentUser) -> dict:
    _ = user
    snapshot = discord_signal_service.active_snapshot()
    return {
        "enabled": discord_signal_service.is_enabled(),
        "window_hours": snapshot.window_hours,
        "active_symbols": snapshot.symbols,
        "pinned_symbols": snapshot.pinned_symbols,
        "options_signals": [
            {
                "symbol": sig.symbol,
                "direction": sig.direction,
                "strike": sig.strike,
                "expiry_raw": sig.expiry_raw,
            }
            for sig in snapshot.options_signals
        ],
        "source_counts": snapshot.source_counts,
        "generated_at": snapshot.generated_at.isoformat(),
        "config": {
            "signal_guild_ids": [g for g in (settings.discord_signal_guild_ids or "").split(",") if g.strip()],
            "signal_channels": [c for c in (settings.discord_signal_channels or "").split(",") if c.strip()],
            "confidence_boost": settings.discord_signal_confidence_boost,
            "max_inject": settings.discord_signal_max_inject,
        },
    }


@router.get("/signals/watchlist", summary="Operator-pinned Discord signal watchlist")
def get_signal_watchlist(user: User = CurrentUser) -> dict:
    _ = user
    entries = discord_signal_service.pinned_entries()
    return {
        "entries": [
            {
                "symbol": e.symbol,
                "asset_class": e.asset_class,
                "source": e.source,
                "note": e.note,
                "pinned_by": e.pinned_by,
                "pinned_at": e.pinned_at.isoformat(),
            }
            for e in entries
        ],
        "count": len(entries),
    }


@router.post("/signals/watchlist/{symbol}", summary="Pin a symbol to Discord signal watchlist")
def pin_signal_symbol(
    payload: PinSymbolRequest,
    symbol: str = Path(min_length=1, max_length=6),
    user: User = HighTrustUser,
) -> dict:
    upper = symbol.strip().upper()
    if not upper or not upper.replace("USD", "").isalpha():
        raise HTTPException(status_code=400, detail="Invalid symbol format")
    entry = discord_signal_service.pin_symbol(
        upper,
        asset_class=payload.asset_class,
        source="manual",
        note=payload.note,
        pinned_by=str(user.email),
    )
    return {
        "ok": True,
        "symbol": entry.symbol,
        "asset_class": entry.asset_class,
        "pinned_at": entry.pinned_at.isoformat(),
    }


@router.delete("/signals/watchlist/{symbol}", summary="Unpin a symbol from Discord signal watchlist")
def unpin_signal_symbol(
    symbol: str = Path(min_length=1, max_length=6),
    user: User = HighTrustUser,
) -> dict:
    _ = user
    upper = symbol.strip().upper()
    deleted = discord_signal_service.unpin_symbol(upper)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Symbol {upper} not in watchlist")
    return {"ok": True, "symbol": upper, "removed": True}
