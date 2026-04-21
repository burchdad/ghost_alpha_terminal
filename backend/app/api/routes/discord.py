from __future__ import annotations

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from app.api.deps.auth import CurrentUser, HighTrustUser
from app.core.config import settings
from app.db.models import User
from app.services.discord_inbound_service import discord_inbound_service
from app.services.discord_notifier import discord_notifier


router = APIRouter(prefix="/discord", tags=["discord"])


class DiscordOutboundRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    severity: str = Field(default="info", min_length=1, max_length=32)


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
