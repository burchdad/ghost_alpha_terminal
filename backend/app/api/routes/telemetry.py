"""
Landing page telemetry tracking for A/B testing and analytics
"""
from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.db.session import get_session
from app.db.models import LandingTelemetryEvent
from app.core.config import settings

router = APIRouter(prefix="/api/telemetry", tags=["telemetry"])


class VariantShownEvent(BaseModel):
    variant_id: str
    event_type: str
    timestamp: str


class CTAClickEvent(BaseModel):
    variant_id: str
    cta_label: str
    event_type: str
    timestamp: str


@router.post("/landing-variant")
async def track_landing_variant(
    event: VariantShownEvent,
):
    """
    Track when a landing page variant is shown to a user.
    Used for A/B testing metrics.
    """
    try:
        with get_session() as session:
            tel_event = LandingTelemetryEvent(
                variant_id=event.variant_id,
                event_type=event.event_type,
                cta_label=None,
                timestamp=datetime.fromisoformat(event.timestamp.replace("Z", "+00:00")),
            )
            session.add(tel_event)
        return {"status": "tracked"}
    except Exception:
        # Silently fail—telemetry should not break UX
        return {"status": "ok"}


@router.post("/landing-cta")
async def track_landing_cta(
    event: CTAClickEvent,
):
    """
    Track CTA clicks on landing page with variant context.
    Used for conversion funnel analysis.
    """
    try:
        with get_session() as session:
            tel_event = LandingTelemetryEvent(
                variant_id=event.variant_id,
                event_type=event.event_type,
                cta_label=event.cta_label,
                timestamp=datetime.fromisoformat(event.timestamp.replace("Z", "+00:00")),
            )
            session.add(tel_event)
        return {"status": "tracked"}
    except Exception:
        # Silently fail
        return {"status": "ok"}


@router.get("/landing-summary")
async def get_landing_summary():
    """
    Get summary of landing page telemetry for analysis.
    Returns variant performance metrics.
    """
    try:
        with get_session() as session:
            # Count variant impressions
            variant_impressions = (
                session.query(
                    LandingTelemetryEvent.variant_id,
                    session.func.count(LandingTelemetryEvent.id).label("count"),
                )
                .filter(LandingTelemetryEvent.event_type == "variant_shown")
                .group_by(LandingTelemetryEvent.variant_id)
                .all()
            )

            # Count CTA clicks by variant
            cta_clicks = (
                session.query(
                    LandingTelemetryEvent.variant_id,
                    LandingTelemetryEvent.cta_label,
                    session.func.count(LandingTelemetryEvent.id).label("count"),
                )
                .filter(LandingTelemetryEvent.event_type == "cta_click")
                .group_by(LandingTelemetryEvent.variant_id, LandingTelemetryEvent.cta_label)
                .all()
            )

            impressions_map = {v: c for v, c in variant_impressions}
            clicks_map = {}
            for variant, cta, count in cta_clicks:
                if variant not in clicks_map:
                    clicks_map[variant] = {}
                clicks_map[variant][cta] = count

            summary = {
                "variant_impressions": impressions_map,
                "cta_clicks": clicks_map,
                "conversion_rates": {
                    v: (
                        sum(clicks_map.get(v, {}).values())
                        / impressions_map.get(v, 1)
                    )
                    if impressions_map.get(v)
                    else 0
                    for v in impressions_map.keys()
                },
            }

            return summary
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
