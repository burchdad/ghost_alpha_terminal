from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from app.services.alpaca_oauth_service import alpaca_oauth_service
from app.services.control_engine import control_engine
from app.services.decision_audit_store import decision_audit_store
from app.services.execution_journal import execution_journal
from app.services.lightweight_metrics import lightweight_metrics
from app.services.live_portfolio_service import live_portfolio_service
from app.services.master_orchestrator import master_orchestrator
from app.services.news.coinbase_ws_service import coinbase_ws_service
from app.services.news.news_intelligence import news_intelligence
from app.services.swarm.execution_bridge import execution_bridge

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get(
    "/lightweight",
    summary="Lightweight launch metrics summary (scans, trades, strategy mix)",
)
def get_lightweight_metrics(days: int = Query(default=7, ge=1, le=30)) -> dict:
    return lightweight_metrics.summary(days=days)


@router.get(
    "/runtime-readiness",
    summary="Operational readiness telemetry for paper soak and live cutover",
)
def get_runtime_readiness() -> dict:
    now = datetime.now(tz=timezone.utc)
    window_start = now - timedelta(hours=24)

    control = control_engine.status()
    latest_scan = master_orchestrator.latest()
    scan_age_seconds: float | None = None
    latest_candidates = 0
    if latest_scan is not None:
        scan_age_seconds = max(0.0, (now - latest_scan.scanned_at).total_seconds())
        latest_candidates = len(latest_scan.candidates)

    executions = execution_journal.recent(limit=500)
    submitted_24h = 0
    rejected_24h = 0
    for item in executions:
        if item.timestamp < window_start:
            continue
        if item.submitted:
            submitted_24h += 1
        else:
            rejected_24h += 1

    audits = decision_audit_store.list_recent(limit=500)
    audits_24h = 0
    for audit in audits:
        ts = audit.get("timestamp")
        if isinstance(ts, datetime) and ts >= window_start:
            audits_24h += 1

    news_entries = news_intelligence.recent_audit(limit=500)
    news_audit_24h = 0
    for entry in news_entries:
        ts = entry.get("timestamp")
        if isinstance(ts, datetime) and ts >= window_start:
            news_audit_24h += 1

    portfolio = live_portfolio_service.snapshot()
    open_positions = len(portfolio.get("active_positions", [])) if portfolio else 0
    connected = alpaca_oauth_service.is_connected()
    mode = execution_bridge.get_mode()
    ws_status = coinbase_ws_service.status()

    return {
        "as_of": now.isoformat(),
        "broker_connected": connected,
        "execution_mode": mode,
        "trading_enabled": bool(control.get("trading_enabled", False)),
        "autonomous_enabled": bool(control.get("autonomous_enabled", False)),
        "autonomous_cycles_run": int(control.get("autonomous_cycles_run", 0)),
        "latest_scan_candidates": latest_candidates,
        "latest_scan_age_seconds": round(scan_age_seconds, 2) if scan_age_seconds is not None else None,
        "open_positions": open_positions,
        "submitted_executions_24h": submitted_24h,
        "rejected_executions_24h": rejected_24h,
        "decision_audits_24h": audits_24h,
        "news_audits_24h": news_audit_24h,
        "coinbase_ws_connected": bool(ws_status.get("connected", False)),
        "coinbase_ws_last_message_at": ws_status.get("last_message_at"),
        "coinbase_ws_error": ws_status.get("last_error"),
        "lightweight_7d": lightweight_metrics.summary(days=7),
    }
