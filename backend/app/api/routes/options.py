from fastapi import APIRouter, HTTPException, Query

from app.api.deps.auth import HighTrustUser
from app.db.models import User
from app.models.schemas import (
    OptionsChainResponse,
    OptionsExecutionRequest,
    OptionsExecutionResponse,
    OptionsRiskAssessmentResponse,
)
from app.services.options_execution_service import options_execution_service
from app.services.options_service import options_service

router = APIRouter(prefix="/options", tags=["options"])

SUPPORTED_STRATEGIES = [
    "LONG_CALL",
    "LONG_PUT",
    "VERTICAL_CALL",
    "VERTICAL_PUT",
    "CALENDAR_CALL",
    "CALENDAR_PUT",
    "DIAGONAL_CALL",
    "DIAGONAL_PUT",
    "RATIO_CALL",
    "RATIO_PUT",
    "BUTTERFLY_CALL",
    "BUTTERFLY_PUT",
    "CONDOR_CALL",
    "CONDOR_PUT",
    "IRON_CONDOR",
    "STRADDLE",
    "STRANGLE",
    "COVERED_CALL",
    "COVERED_PUT",
    "PROTECTIVE_CALL",
    "PROTECTIVE_PUT",
    "CUSTOM_2_LEG",
    "CUSTOM_3_LEG",
    "CUSTOM_4_LEG",
    "CUSTOM_STOCK_OPTION",
]


@router.get("/strategies/supported", response_model=list[str])
def get_supported_option_strategies() -> list[str]:
    return SUPPORTED_STRATEGIES


@router.post("/risk/preview", response_model=OptionsRiskAssessmentResponse)
def preview_options_risk(payload: OptionsExecutionRequest, user: User = HighTrustUser) -> OptionsRiskAssessmentResponse:
    del user
    try:
        response = options_execution_service.preview_or_execute(payload.model_copy(update={"preview": True}))
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    if response.risk is None:
        raise HTTPException(status_code=422, detail="Unable to build an option strategy plan for risk preview")
    return response.risk


@router.post("/execute", response_model=OptionsExecutionResponse)
def execute_options_trade(payload: OptionsExecutionRequest, user: User = HighTrustUser) -> OptionsExecutionResponse:
    del user
    try:
        return options_execution_service.preview_or_execute(payload)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err


@router.get("/{symbol}/expirations", response_model=list[str])
def get_option_expirations(symbol: str) -> list[str]:
    return options_service.get_available_expirations(symbol=symbol)


@router.get("/{symbol}", response_model=OptionsChainResponse)
def get_options(symbol: str, expiration: str | None = Query(default=None)) -> OptionsChainResponse:
    return options_service.get_options_chain(symbol=symbol, expiration=expiration)
