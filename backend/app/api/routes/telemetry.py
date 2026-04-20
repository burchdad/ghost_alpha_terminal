"""
Landing page telemetry tracking for A/B testing and analytics
"""
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func

from app.db.session import get_session
from app.db.models import (
    AuthAuditLog,
    BrokerOAuthConnection,
    ExecutionJournalDB,
    LandingTelemetryEvent,
    User,
    UserSession,
)
from app.core.config import settings

router = APIRouter(prefix="/telemetry", tags=["telemetry"])


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
                    func.count(LandingTelemetryEvent.id).label("count"),
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
                    func.count(LandingTelemetryEvent.id).label("count"),
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


@router.get("/ops-summary", summary="Launch operations summary (funnel + reliability)")
async def get_ops_summary() -> dict:
    """Operational launch dashboard payload for quick daily decision-making."""
    now = datetime.now(tz=timezone.utc)
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)

    try:
        with get_session() as session:
            users_total = int(session.query(func.count(User.id)).scalar() or 0)
            users_7d = int(
                session.query(func.count(User.id))
                .filter(User.created_at >= week_ago)
                .scalar()
                or 0
            )

            users_twofa_verified = int(
                session.query(func.count(User.id))
                .filter(User.twofa_verified.is_(True))
                .scalar()
                or 0
            )

            connected_broker_rows = (
                session.query(BrokerOAuthConnection.user_id)
                .filter(BrokerOAuthConnection.connected.is_(True))
                .distinct()
                .all()
            )
            users_with_connected_broker = len(connected_broker_rows)

            active_sessions_24h = int(
                session.query(func.count(UserSession.id))
                .filter(UserSession.created_at >= day_ago)
                .filter(UserSession.revoked_at.is_(None))
                .scalar()
                or 0
            )

            auth_failed_24h = int(
                session.query(func.count(AuthAuditLog.id))
                .filter(AuthAuditLog.created_at >= day_ago)
                .filter(AuthAuditLog.status.in_(["failed", "invalid_token", "replay_blocked", "unknown_account"]))
                .scalar()
                or 0
            )

            executions_24h = int(
                session.query(func.count(ExecutionJournalDB.id))
                .filter(ExecutionJournalDB.timestamp >= day_ago)
                .scalar()
                or 0
            )
            execution_submitted_24h = int(
                session.query(func.count(ExecutionJournalDB.id))
                .filter(ExecutionJournalDB.timestamp >= day_ago)
                .filter(ExecutionJournalDB.submitted.is_(True))
                .scalar()
                or 0
            )
            execution_errors_24h = int(
                session.query(func.count(ExecutionJournalDB.id))
                .filter(ExecutionJournalDB.timestamp >= day_ago)
                .filter(ExecutionJournalDB.error.isnot(None))
                .scalar()
                or 0
            )

            funnel = {
                "registered_users": users_total,
                "twofa_verified_users": users_twofa_verified,
                "users_with_connected_broker": users_with_connected_broker,
                "symbols_with_submitted_execution_24h": int(
                    session.query(func.count(func.distinct(ExecutionJournalDB.symbol)))
                    .filter(ExecutionJournalDB.timestamp >= day_ago)
                    .filter(ExecutionJournalDB.submitted.is_(True))
                    .scalar()
                    or 0
                ),
            }

            def pct(numerator: int, denominator: int) -> float:
                if denominator <= 0:
                    return 0.0
                return round((numerator / denominator) * 100.0, 2)

            conversions = {
                "signup_to_twofa_verified_pct": pct(users_twofa_verified, users_total),
                "twofa_verified_to_broker_connected_pct": pct(users_with_connected_broker, users_twofa_verified),
            }

            reliability = {
                "active_sessions_24h": active_sessions_24h,
                "auth_failures_24h": auth_failed_24h,
                "executions_total_24h": executions_24h,
                "executions_submitted_24h": execution_submitted_24h,
                "execution_errors_24h": execution_errors_24h,
                "execution_submit_rate_pct": pct(execution_submitted_24h, executions_24h),
                "execution_error_rate_pct": pct(execution_errors_24h, max(executions_24h, 1)),
            }

            return {
                "generated_at": now.isoformat(),
                "window": {
                    "last_24h_start": day_ago.isoformat(),
                    "last_7d_start": week_ago.isoformat(),
                },
                "growth": {
                    "users_total": users_total,
                    "users_created_7d": users_7d,
                },
                "funnel": funnel,
                "conversions": conversions,
                "reliability": reliability,
            }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        )
