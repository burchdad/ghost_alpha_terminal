"""
Notifications API
=================
GET  /notifications/stream    — SSE event stream (real-time push)
GET  /notifications           — recent notification history
POST /notifications/{id}/read — mark one notification read
POST /notifications/read-all  — mark all read
GET  /notifications/unread-count — unread badge count
"""
from __future__ import annotations

import asyncio
from dataclasses import asdict

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.api.deps.auth import CurrentUser
from app.db.models import User
from app.services.notification_service import notification_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/stream")
async def notification_stream(user: User = CurrentUser) -> StreamingResponse:
    """
    Server-Sent Events stream.  Clients keep this connection open and receive
    real-time notification events as they are emitted by the backend.
    """
    _ = user
    queue = notification_service.subscribe_sse()

    async def event_generator():
        # Send a keep-alive comment immediately so the browser knows the stream is live
        yield ": connected\n\n"
        try:
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=25.0)
                    yield event.to_sse()
                except asyncio.TimeoutError:
                    # Send heartbeat to keep connection alive through proxies
                    yield ": heartbeat\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            notification_service.unsubscribe_sse(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("")
def get_notifications(user: User = CurrentUser, limit: int = 50) -> dict:
    _ = user
    items = notification_service.history(limit=min(limit, 100))
    return {
        "notifications": [asdict(ev) for ev in items],
        "unread_count": notification_service.unread_count(),
    }


@router.get("/unread-count")
def get_unread_count(user: User = CurrentUser) -> dict:
    _ = user
    return {"unread_count": notification_service.unread_count()}


@router.post("/{event_id}/read")
def mark_read(event_id: str, user: User = CurrentUser) -> dict:
    _ = user
    found = notification_service.mark_read(event_id)
    return {"ok": found, "event_id": event_id}


@router.post("/read-all")
def mark_all_read(user: User = CurrentUser) -> dict:
    _ = user
    count = notification_service.mark_all_read()
    return {"ok": True, "marked_read": count}
