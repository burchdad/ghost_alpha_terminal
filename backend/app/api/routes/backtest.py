from fastapi import APIRouter

from app.models.schemas import BacktestRequest, BacktestResponse
from app.services.backtest_engine import backtest_engine

router = APIRouter(prefix="/backtest", tags=["backtest"])


@router.post("", response_model=BacktestResponse)
def run_backtest(payload: BacktestRequest) -> BacktestResponse:
    return backtest_engine.run_backtest(payload)
