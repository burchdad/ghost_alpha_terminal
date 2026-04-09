from fastapi import APIRouter

from app.models.schemas import (
    AutonomousModeStatusResponse,
    AutonomousModeUpdateRequest,
    ControlStatusResponse,
    GoalMissionRequest,
    GoalMissionResponse,
    GoalStatusResponse,
    GoalTargetRequest,
    KillSwitchUpdateRequest,
    KillSwitchUpdateResponse,
    RiskLimitUpdateRequest,
    RiskLimitUpdateResponse,
)
from app.services.autonomous_runner import autonomous_runner
from app.services.control_engine import control_engine
from app.services.execution_journal import execution_journal
from app.services.goal_engine import goal_engine
from app.services.live_portfolio_service import live_portfolio_service
from app.services.portfolio_manager import portfolio_manager
from app.services.swarm.execution_bridge import execution_bridge

router = APIRouter(prefix="/control", tags=["control"])


@router.get("", response_model=ControlStatusResponse)
def get_control_status() -> ControlStatusResponse:
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

    deduped: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for item in sorted(merged_rejections, key=lambda x: x.get("timestamp")):
        ts = item.get("timestamp")
        key = (str(ts), str(item.get("symbol", "")), str(item.get("reason", "")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    # Keep payload bounded while preserving chronological order for UI slice(-5).
    deduped = deduped[-200:]

    return ControlStatusResponse(
        **status,
        rejected_trades=deduped,
        autonomous_enabled=auto["enabled"],
        autonomous_interval_seconds=auto["interval_seconds"],
        autonomous_symbols=auto["symbols"],
        autonomous_cycles_run=auto["cycles_run"],
        autonomous_last_run_at=auto["last_run_at"],
        autonomous_last_error=auto["last_error"],
    )


@router.post("/kill-switch", response_model=KillSwitchUpdateResponse)
def update_kill_switch(payload: KillSwitchUpdateRequest) -> KillSwitchUpdateResponse:
    enabled = control_engine.set_kill_switch(payload.trading_enabled)
    return KillSwitchUpdateResponse(
        trading_enabled=enabled,
        system_status="ACTIVE" if enabled else "PAUSED",
    )


@router.post("/limits", response_model=RiskLimitUpdateResponse)
def update_risk_limits(payload: RiskLimitUpdateRequest) -> RiskLimitUpdateResponse:
    result = control_engine.set_limits(
        daily_loss_limit_pct=payload.daily_loss_limit_pct,
        max_drawdown_limit_pct=payload.max_drawdown_limit_pct,
    )
    return RiskLimitUpdateResponse(**result)


@router.get("/autonomous", response_model=AutonomousModeStatusResponse)
def get_autonomous_status() -> AutonomousModeStatusResponse:
    return AutonomousModeStatusResponse(**autonomous_runner.status())


@router.post("/autonomous", response_model=AutonomousModeStatusResponse)
def update_autonomous(payload: AutonomousModeUpdateRequest) -> AutonomousModeStatusResponse:
    return AutonomousModeStatusResponse(
        **autonomous_runner.configure(
            enabled=payload.enabled,
            interval_seconds=payload.interval_seconds,
            symbols=payload.symbols,
        )
    )


@router.post("/autonomous/run-once", response_model=AutonomousModeStatusResponse)
def run_autonomous_once() -> AutonomousModeStatusResponse:
    return AutonomousModeStatusResponse(**autonomous_runner.trigger_run_once())


def _current_capital() -> float:
    portfolio = live_portfolio_service.snapshot() or portfolio_manager.snapshot()
    return float(portfolio.get("account_balance", 0.0) or 0.0)


@router.get("/goal", response_model=GoalStatusResponse)
def get_goal_status() -> GoalStatusResponse:
    return GoalStatusResponse(**goal_engine.status(current_capital=_current_capital()))


@router.post("/goal", response_model=GoalStatusResponse)
def set_goal(payload: GoalTargetRequest) -> GoalStatusResponse:
    status = goal_engine.configure(
        start_capital=payload.start_capital,
        target_capital=payload.target_capital,
        timeframe_days=payload.timeframe_days,
    )
    return GoalStatusResponse(**status)


@router.delete("/goal", response_model=GoalStatusResponse)
def clear_goal() -> GoalStatusResponse:
    goal_engine.clear()
    return GoalStatusResponse(**goal_engine.status(current_capital=_current_capital()))


@router.post("/mission", response_model=GoalMissionResponse)
def start_goal_mission(payload: GoalMissionRequest) -> GoalMissionResponse:
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
    )
    if payload.autonomous_enabled and payload.trigger_initial_cycle:
        autonomous_status = autonomous_runner.trigger_run_once()

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
