from fastapi import APIRouter

from app.models.schemas import BacktestRequest, BacktestResponse, ControlledExperimentResponse
from app.services.backtest_engine import backtest_engine

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("", response_model=BacktestResponse)
def run_backtest(payload: BacktestRequest) -> BacktestResponse:
    return backtest_engine.run_backtest(payload)


@router.post("/controlled-experiments", response_model=ControlledExperimentResponse)
def run_controlled_experiments(payload: BacktestRequest) -> ControlledExperimentResponse:
    return backtest_engine.run_controlled_experiments(payload)
