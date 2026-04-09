from fastapi import APIRouter

from app.models.schemas import (
    AutonomousModeStatusResponse,
    AutonomousModeUpdateRequest,
    ControlStatusResponse,
    KillSwitchUpdateRequest,
    KillSwitchUpdateResponse,
)
from app.services.autonomous_runner import autonomous_runner
from app.services.control_engine import control_engine

router = APIRouter(prefix="/control", tags=["control"])


@router.get("", response_model=ControlStatusResponse)
def get_control_status() -> ControlStatusResponse:
    status = control_engine.status()
    auto = autonomous_runner.status()
    return ControlStatusResponse(
        **status,
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
    return AutonomousModeStatusResponse(**autonomous_runner.run_once())
