from __future__ import annotations

from datetime import datetime, timedelta, timezone
from collections import defaultdict

from fastapi import APIRouter, Query

from app.services.alpaca_oauth_service import alpaca_oauth_service
from app.services.autonomous_runner import autonomous_runner
from app.services.control_engine import control_engine
from app.services.decision_audit_store import decision_audit_store
from app.services.execution_journal import execution_journal
from app.services.lightweight_metrics import lightweight_metrics
from app.services.live_portfolio_service import live_portfolio_service
from app.services.master_orchestrator import master_orchestrator
from app.services.mission_intelligence_service import mission_intelligence_service
from app.services.news.coinbase_ws_service import coinbase_ws_service
from app.services.news.news_intelligence import news_intelligence
from app.services.swarm.execution_bridge import execution_bridge

router = APIRouter(prefix="/metrics", tags=["metrics"])


def _as_utc(dt: datetime | None) -> datetime | None:
    if not isinstance(dt, datetime):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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

    try:
        control = control_engine.status()
    except Exception:
        control = {}

    try:
        autonomous = autonomous_runner.status()
    except Exception:
        autonomous = {}

    try:
        latest_scan = master_orchestrator.latest()
    except Exception:
        latest_scan = None

    scan_age_seconds: float | None = None
    latest_candidates = 0
    if latest_scan is not None:
        scanned_at = _as_utc(getattr(latest_scan, "scanned_at", None))
        if scanned_at is not None:
            scan_age_seconds = max(0.0, (now - scanned_at).total_seconds())
        latest_candidates = len(latest_scan.candidates)

    try:
        executions = execution_journal.recent(limit=500)
    except Exception:
        executions = []

    submitted_24h = 0
    rejected_24h = 0
    for item in executions:
        ts = getattr(item, "timestamp", None)
        if not isinstance(ts, datetime) or ts < window_start:
            continue
        if item.submitted:
            submitted_24h += 1
        else:
            rejected_24h += 1

    try:
        audits = decision_audit_store.list_recent(limit=500)
    except Exception:
        audits = []

    audits_24h = 0
    for audit in audits:
        ts = _as_utc(audit.get("timestamp"))
        if ts is not None and ts >= window_start:
            audits_24h += 1

    try:
        news_entries = news_intelligence.recent_audit(limit=500)
    except Exception:
        news_entries = []

    news_audit_24h = 0
    for entry in news_entries:
        ts = _as_utc(entry.get("timestamp"))
        if ts is not None and ts >= window_start:
            news_audit_24h += 1

    try:
        portfolio = live_portfolio_service.snapshot()
    except Exception:
        portfolio = None
    open_positions = len(portfolio.get("active_positions", [])) if portfolio else 0

    try:
        connected = alpaca_oauth_service.is_connected()
    except Exception:
        connected = False

    try:
        mode = execution_bridge.get_mode()
    except Exception:
        mode = "SIMULATION"

    try:
        ws_status = coinbase_ws_service.status()
    except Exception:
        ws_status = {}

    try:
        lightweight = lightweight_metrics.summary(days=7)
    except Exception:
        lightweight = {
            "window_days": 7,
            "start_day": now.date().isoformat(),
            "end_day": now.date().isoformat(),
            "scans_run": 0,
            "trades_triggered": 0,
            "strategies_selected": {},
            "top_strategies": [],
        }

    return {
        "as_of": now.isoformat(),
        "broker_connected": connected,
        "execution_mode": mode,
        "trading_enabled": bool(control.get("trading_enabled", False)),
        "autonomous_enabled": bool(autonomous.get("enabled", False)),
        "autonomous_cycles_run": int(autonomous.get("cycles_run", 0)),
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
        "lightweight_7d": lightweight,
    }


@router.get(
    "/mission-intelligence",
    summary="Mission policy, capital buckets, sprint governance, execution quality, and parity watchdog",
)
def get_mission_intelligence() -> dict:
    return mission_intelligence_service.snapshot()


@router.get(
    "/truth-dashboard",
    summary="Trading truth dashboard metrics (trades, win rate, PnL, and strategy leaders)",
)
def get_truth_dashboard(days: int = Query(default=7, ge=1, le=30)) -> dict:
    now = datetime.now(tz=timezone.utc)
    window_start = now - timedelta(days=days)

    entries = execution_journal.recent(limit=2000)
    window_entries = [
        row
        for row in entries
        if isinstance(row.timestamp, datetime) and _as_utc(row.timestamp) is not None and _as_utc(row.timestamp) >= window_start
    ]

    trades = sum(1 for row in window_entries if bool(row.submitted))
    settled = [row for row in window_entries if str(row.outcome_label or "").upper() in {"WIN", "LOSS"} and row.pnl is not None]
    wins = sum(1 for row in settled if str(row.outcome_label or "").upper() == "WIN")
    net_pnl = sum(float(row.pnl or 0.0) for row in settled)
    win_rate = wins / max(len(settled), 1)

    by_strategy: dict[str, list] = defaultdict(list)
    for row in settled:
        by_strategy[str(row.strategy or "UNKNOWN").upper()].append(row)

    strategy_stats: list[dict] = []
    for strategy, rows in by_strategy.items():
        strategy_pnl = sum(float(item.pnl or 0.0) for item in rows)
        strategy_wins = sum(1 for item in rows if str(item.outcome_label or "").upper() == "WIN")
        strategy_stats.append(
            {
                "strategy": strategy,
                "trades": len(rows),
                "win_rate": round(strategy_wins / max(len(rows), 1), 4),
                "net_pnl": round(strategy_pnl, 2),
            }
        )

    best_strategy = max(strategy_stats, key=lambda item: item["net_pnl"], default=None)
    worst_strategy = min(strategy_stats, key=lambda item: item["net_pnl"], default=None)

    return {
        "window_days": days,
        "as_of": now.isoformat(),
        "trades": trades,
        "settled_trades": len(settled),
        "win_rate": round(win_rate, 4),
        "net_pnl": round(net_pnl, 2),
        "best_strategy": best_strategy,
        "worst_strategy": worst_strategy,
        "strategy_breakdown": sorted(strategy_stats, key=lambda item: item["net_pnl"], reverse=True),
    }
