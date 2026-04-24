import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.api.deps.auth import CurrentUser, HighTrustUser
from app.db.models import User

from app.models.schemas import (
    AutonomousModeStatusResponse,
    AutonomousModeUpdateRequest,
    ControlStatusResponse,
    GoalMissionRequest,
    GoalMissionResponse,
    GoalStatusResponse,
    OptionsSprintStatusResponse,
    OptionsSprintUpdateRequest,
    GoalTargetRequest,
    KillSwitchUpdateRequest,
    KillSwitchUpdateResponse,
    NewsFeedSettingsResponse,
    NewsFeedSettingsUpdateRequest,
    RiskLimitUpdateRequest,
    RiskLimitUpdateResponse,
)
from app.services.autonomous_runner import autonomous_runner
from app.services.control_engine import control_engine
from app.services.decision_audit_store import decision_audit_store
from app.services.execution_quality_engine import execution_quality_engine
from app.services.execution_journal import execution_journal
from app.services.goal_engine import goal_engine
from app.services.live_portfolio_service import live_portfolio_service
from app.services.mission_intelligence_service import mission_intelligence_service
from app.services.news.news_intelligence import news_intelligence
from app.services.news_feed_settings_service import news_feed_settings_service
from app.services.live_experiment_promotion_service import live_experiment_promotion_service
from app.services.meta_risk_governor import meta_risk_governor
from app.services.options_sprint_service import options_sprint_service
from app.services.portfolio_manager import portfolio_manager
from app.services.strategy_kill_switch_service import strategy_kill_switch_service
from app.services.strategy_lifecycle_transition_store import strategy_lifecycle_transition_store
from app.services.system_mode_service import system_mode_service
from app.services.swarm.execution_bridge import execution_bridge
from app.services.notification_service import notification_service

router = APIRouter(prefix="/control", tags=["control"])
logger = logging.getLogger(__name__)


def _coerce_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            return None

    return None


@router.get("", response_model=ControlStatusResponse)
def get_control_status(user: User = CurrentUser) -> ControlStatusResponse:
    try:
        status = control_engine.status()
        auto = autonomous_runner.status()
        merged_rejections = list(status.get("rejected_trades", []))

        try:
            # Include execution-level non-submitted outcomes (e.g., HOLD / veto / broker rejection)
            # so Safety & Control aligns with Decision Replay and audit trail status.
            executions = execution_journal.recent(limit=200)
            for entry in executions:
                if entry.submitted:
                    continue
                merged_rejections.append(
                    {
                        "timestamp": entry.timestamp,
                        "symbol": entry.symbol,
                        "reason": entry.reason or "Execution not submitted.",
                    }
                )
        except Exception:
            pass

        try:
            # Include decision-audit rejections for paths that do not write to control_engine reject log.
            rejected_audits = decision_audit_store.list_recent(limit=200, status="REJECTED")
            for audit in rejected_audits:
                merged_rejections.append(
                    {
                        "timestamp": audit.get("timestamp"),
                        "symbol": str(audit.get("symbol", "N/A")),
                        "reason": "Decision audit marked REJECTED.",
                    }
                )
        except Exception:
            pass

        normalized: list[dict] = []
        for item in merged_rejections:
            ts = _coerce_timestamp(item.get("timestamp"))
            symbol = str(item.get("symbol", "")).strip().upper()
            reason = str(item.get("reason", "")).strip()
            if ts is None or not symbol or not reason:
                continue
            normalized.append({"timestamp": ts, "symbol": symbol, "reason": reason})

        deduped: list[dict] = []
        seen: set[tuple[str, str, str]] = set()
        for item in sorted(normalized, key=lambda x: x["timestamp"]):
            key = (
                item["timestamp"].isoformat(),
                item["symbol"],
                item["reason"],
            )
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)

        # Keep payload bounded while preserving chronological order for UI slice(-5).
        deduped = deduped[-200:]

        status_payload = {**status, "rejected_trades": deduped}

        return ControlStatusResponse(
            **status_payload,
            autonomous_enabled=bool(auto.get("enabled", False)),
            autonomous_interval_seconds=int(auto.get("interval_seconds", 300)),
            autonomous_symbols=list(auto.get("symbols", [])),
            autonomous_cycles_run=int(auto.get("cycles_run", 0)),
            autonomous_last_run_at=_coerce_timestamp(auto.get("last_run_at")),
            autonomous_last_error=auto.get("last_error"),
            options_sprint=OptionsSprintStatusResponse(**options_sprint_service.status()),
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("control_status_failed: %s", exc)
        return ControlStatusResponse(
            trading_enabled=False,
            system_status="PAUSED",
            mode="SAFE",
            daily_pnl=0.0,
            daily_loss=0.0,
            daily_loss_limit=5000.0,
            daily_loss_limit_pct=0.05,
            rolling_drawdown=0.0,
            rolling_drawdown_pct=0.0,
            max_drawdown_limit_pct=0.10,
            rejected_trades=[],
            autonomous_enabled=False,
            autonomous_interval_seconds=300,
            autonomous_symbols=[],
            autonomous_cycles_run=0,
            autonomous_last_run_at=None,
            autonomous_last_error="Control status temporarily unavailable; using fallback.",
            options_sprint=OptionsSprintStatusResponse(**options_sprint_service.status()),
        )


@router.post("/kill-switch", response_model=KillSwitchUpdateResponse)
def update_kill_switch(payload: KillSwitchUpdateRequest, user: User = HighTrustUser) -> KillSwitchUpdateResponse:
    enabled = control_engine.set_kill_switch(payload.trading_enabled)
    try:
        notification_service.kill_switch_changed(
            enabled=not enabled,  # set_kill_switch returns trading_enabled; kill_switch_enabled = not trading_enabled
            changed_by=getattr(user, "email", "operator"),
        )
    except Exception:
        pass
    return KillSwitchUpdateResponse(
        trading_enabled=enabled,
        system_status="ACTIVE" if enabled else "PAUSED",
    )


@router.post("/limits", response_model=RiskLimitUpdateResponse)
def update_risk_limits(payload: RiskLimitUpdateRequest, user: User = HighTrustUser) -> RiskLimitUpdateResponse:
    result = control_engine.set_limits(
        daily_loss_limit_pct=payload.daily_loss_limit_pct,
        max_drawdown_limit_pct=payload.max_drawdown_limit_pct,
    )
    return RiskLimitUpdateResponse(**result)


@router.get("/autonomous", response_model=AutonomousModeStatusResponse)
def get_autonomous_status(user: User = CurrentUser) -> AutonomousModeStatusResponse:
    return AutonomousModeStatusResponse(**autonomous_runner.status())


@router.post("/autonomous", response_model=AutonomousModeStatusResponse)
def update_autonomous(payload: AutonomousModeUpdateRequest, user: User = HighTrustUser) -> AutonomousModeStatusResponse:
    return AutonomousModeStatusResponse(
        **autonomous_runner.configure(
            enabled=payload.enabled,
            interval_seconds=payload.interval_seconds,
            symbols=payload.symbols,
            user_id=str(user.id),
        )
    )


@router.post("/autonomous/run-once", response_model=AutonomousModeStatusResponse)
def run_autonomous_once(user: User = HighTrustUser) -> AutonomousModeStatusResponse:
    return AutonomousModeStatusResponse(**autonomous_runner.trigger_run_once(user_id=str(user.id)))


def _news_feed_settings_payload() -> dict:
    catalog = news_intelligence.public_feed_catalog()
    runtime = news_feed_settings_service.status()
    enabled = {item.strip().upper() for item in runtime.get("enabled_sources", []) if str(item).strip()}
    weights = {
        str(source).strip().upper(): float(weight)
        for source, weight in runtime.get("source_weights", {}).items()
        if str(source).strip()
    }
    return {
        "sources": [
            {
                "source": item["source"],
                "url": item["url"],
                "enabled": item["source"] in enabled,
                "weight": float(weights.get(item["source"], 1.0)),
            }
            for item in catalog
        ],
        "refresh_seconds": int(runtime.get("refresh_seconds", 45)),
        "updated_at": runtime.get("updated_at"),
    }


@router.get("/news-feeds", response_model=NewsFeedSettingsResponse)
def get_news_feed_settings(user: User = CurrentUser) -> NewsFeedSettingsResponse:
    return NewsFeedSettingsResponse(**_news_feed_settings_payload())


@router.post("/news-feeds", response_model=NewsFeedSettingsResponse)
def update_news_feed_settings(payload: NewsFeedSettingsUpdateRequest, user: User = CurrentUser) -> NewsFeedSettingsResponse:
    valid_sources = {item["source"] for item in news_intelligence.public_feed_catalog()}
    requested_sources = [item.strip().upper() for item in payload.enabled_sources if item.strip()]
    invalid_sources = sorted({item for item in requested_sources if item not in valid_sources})
    if invalid_sources:
        raise HTTPException(status_code=400, detail=f"Unsupported news sources: {', '.join(invalid_sources)}")

    requested_weights = {key.strip().upper(): float(value) for key, value in payload.source_weights.items() if key.strip()}
    invalid_weight_sources = sorted({key for key in requested_weights if key not in valid_sources and key not in {"ALPACA_NEWS", "COINBASE_WS_PUBLIC"}})
    if invalid_weight_sources:
        raise HTTPException(status_code=400, detail=f"Unsupported source weights: {', '.join(invalid_weight_sources)}")

    news_feed_settings_service.configure(
        enabled_sources=requested_sources,
        source_weights=requested_weights,
    )
    news_intelligence.invalidate_cached_feeds()
    return NewsFeedSettingsResponse(**_news_feed_settings_payload())


def _current_capital() -> float:
    portfolio = live_portfolio_service.snapshot() or portfolio_manager.snapshot()
    return float(portfolio.get("account_balance", 0.0) or 0.0)


@router.get("/goal", response_model=GoalStatusResponse)
def get_goal_status(user: User = CurrentUser) -> GoalStatusResponse:
    return GoalStatusResponse(**goal_engine.status(current_capital=_current_capital()))


@router.post("/goal", response_model=GoalStatusResponse)
def set_goal(payload: GoalTargetRequest, user: User = HighTrustUser) -> GoalStatusResponse:
    status = goal_engine.configure(
        start_capital=payload.start_capital,
        target_capital=payload.target_capital,
        timeframe_days=payload.timeframe_days,
    )
    return GoalStatusResponse(**status)


@router.delete("/goal", response_model=GoalStatusResponse)
def clear_goal(user: User = HighTrustUser) -> GoalStatusResponse:
    goal_engine.clear()
    return GoalStatusResponse(**goal_engine.status(current_capital=_current_capital()))


@router.get("/options-sprint", response_model=OptionsSprintStatusResponse)
def get_options_sprint_status(user: User = CurrentUser) -> OptionsSprintStatusResponse:
    return OptionsSprintStatusResponse(**options_sprint_service.status())


@router.post("/options-sprint", response_model=OptionsSprintStatusResponse)
def set_options_sprint(payload: OptionsSprintUpdateRequest, user: User = HighTrustUser) -> OptionsSprintStatusResponse:
    status = options_sprint_service.configure(
        enabled=payload.enabled,
        target_amount=payload.target_amount,
        timeframe_days=payload.timeframe_days,
        objective_summary=payload.objective_summary,
        activation_source=payload.activation_source,
        acknowledged_high_risk=payload.acknowledged_high_risk,
        allow_live_execution=payload.allow_live_execution,
    )
    return OptionsSprintStatusResponse(**status)


@router.delete("/options-sprint", response_model=OptionsSprintStatusResponse)
def clear_options_sprint(user: User = HighTrustUser) -> OptionsSprintStatusResponse:
    return OptionsSprintStatusResponse(**options_sprint_service.clear())


@router.post("/mission", response_model=GoalMissionResponse)
def start_goal_mission(payload: GoalMissionRequest, user: User = HighTrustUser) -> GoalMissionResponse:
    current_capital = _current_capital()
    start_capital = float(payload.start_capital) if payload.start_capital is not None else current_capital

    goal_status = goal_engine.configure(
        start_capital=start_capital,
        target_capital=payload.target_capital,
        timeframe_days=payload.timeframe_days,
    )

    if payload.execution_mode is not None:
        execution_mode = execution_bridge.set_mode(payload.execution_mode)
    else:
        execution_mode = execution_bridge.get_mode()

    trading_enabled = control_engine.set_kill_switch(payload.trading_enabled)

    autonomous_status = autonomous_runner.configure(
        enabled=payload.autonomous_enabled,
        interval_seconds=payload.interval_seconds,
        symbols=payload.symbols,
        user_id=str(user.id),
    )
    if payload.autonomous_enabled and payload.trigger_initial_cycle:
        autonomous_status = autonomous_runner.trigger_run_once(user_id=str(user.id))

    return GoalMissionResponse(
        message=(
            "Mission configured. Goal engine, execution mode, and autonomous runner are now synchronized. "
            "Ghost Alpha will handle opportunity discovery, strategy selection, and execution gating internally."
        ),
        execution_mode=execution_mode,
        trading_enabled=trading_enabled,
        goal=goal_status,
        autonomous=autonomous_status,
    )


@router.get("/mission/simulate")
def simulate_mission(target_capital: float, timeframe_days: int, start_capital: float | None = None, user: User = CurrentUser) -> dict:
    return mission_intelligence_service.simulate_mission(
        target_capital=target_capital,
        timeframe_days=timeframe_days,
        start_capital=start_capital,
    )


@router.get("/strategy-kill-switch")
def get_strategy_kill_switch_overrides(user: User = CurrentUser) -> dict:
    return {
        "manual_force_enabled": strategy_kill_switch_service.list_force_enabled(),
    }


@router.post("/strategy-kill-switch/override")
def set_strategy_kill_switch_override(strategy: str, force_enabled: bool = True, user: User = HighTrustUser) -> dict:
    result = strategy_kill_switch_service.set_force_enabled(strategy=strategy, enabled=force_enabled)
    return {
        **result,
        "manual_force_enabled": strategy_kill_switch_service.list_force_enabled(),
    }


@router.delete("/strategy-kill-switch/override")
def clear_strategy_kill_switch_override(strategy: str, user: User = HighTrustUser) -> dict:
    result = strategy_kill_switch_service.clear_force_enabled(strategy=strategy)
    return {
        **result,
        "manual_force_enabled": strategy_kill_switch_service.list_force_enabled(),
    }


@router.get("/strategy-lifecycle-transitions")
def get_strategy_lifecycle_transitions(limit: int = 200, since_hours: int = 168, user: User = CurrentUser) -> dict:
    bounded_limit = max(1, min(limit, 1000))
    bounded_since = max(1, min(since_hours, 24 * 30))
    return {
        "recent": strategy_lifecycle_transition_store.recent(limit=bounded_limit, since_hours=bounded_since),
        "summary": strategy_lifecycle_transition_store.summary(since_hours=bounded_since),
    }


@router.post("/admin/reset-runtime-state")
def reset_runtime_state(*, reset_live_mode: bool = True, reset_meta_risk: bool = True, reset_system_mode: bool = True, user: User = HighTrustUser) -> dict:
    result: dict = {
        "reset_live_mode": bool(reset_live_mode),
        "reset_meta_risk": bool(reset_meta_risk),
        "reset_system_mode": bool(reset_system_mode),
    }

    if reset_live_mode:
        result["live_experiment_mode"] = live_experiment_promotion_service.reset_to_default(source="admin_reset")
    else:
        result["live_experiment_mode"] = live_experiment_promotion_service.status()

    if reset_meta_risk:
        result["meta_risk_governor"] = meta_risk_governor.reset_cooldown()
    else:
        control = control_engine.status()
        result["meta_risk_governor"] = meta_risk_governor.evaluate(
            drawdown_pct=float(control.get("rolling_drawdown_pct", 0.0) or 0.0)
        )

    if reset_system_mode:
        result["system_mode"] = system_mode_service.reset_to_default(source="admin_reset")
    else:
        control = control_engine.status()
        goal = goal_engine.status(current_capital=float((live_portfolio_service.snapshot() or portfolio_manager.snapshot()).get("account_balance", 0.0) or 0.0))
        result["system_mode"] = system_mode_service.evaluate(
            goal_pressure=float(goal.get("goal_pressure_multiplier", 1.0) or 1.0),
            drawdown_pct=float(control.get("rolling_drawdown_pct", 0.0) or 0.0),
            quality=execution_quality_engine.summary(limit=500),
            meta_risk=result["meta_risk_governor"],
            live_mode=live_experiment_promotion_service.status(),
        )

    return result
