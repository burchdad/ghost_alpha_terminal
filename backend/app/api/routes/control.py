from fastapi import APIRouter

from app.models.schemas import (
    ControlStatusResponse,
    KillSwitchUpdateRequest,
    KillSwitchUpdateResponse,
)
from app.services.control_engine import control_engine

router = APIRouter(prefix="/control", tags=["control"])


@router.get("", response_model=ControlStatusResponse)
def get_control_status() -> ControlStatusResponse:
    return ControlStatusResponse(**control_engine.status())


@router.post("/kill-switch", response_model=KillSwitchUpdateResponse)
def update_kill_switch(payload: KillSwitchUpdateRequest) -> KillSwitchUpdateResponse:
    enabled = control_engine.set_kill_switch(payload.trading_enabled)
    return KillSwitchUpdateResponse(
        trading_enabled=enabled,
        system_status="ACTIVE" if enabled else "PAUSED",
    )
