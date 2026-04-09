from __future__ import annotations

from fastapi import APIRouter, Query

from app.services.lightweight_metrics import lightweight_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "/lightweight",
    summary="Lightweight launch metrics summary (scans, trades, strategy mix)",
)
def get_lightweight_metrics(days: int = Query(default=7, ge=1, le=30)) -> dict:
    return lightweight_metrics.summary(days=days)
