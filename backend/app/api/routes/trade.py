from fastapi import APIRouter

from app.api.deps.auth import HighTrustUser
from app.db.models import User
from app.models.schemas import TradeOutcomeRequest, TradeOutcomeResponse
from app.services.agent_scorer import agent_scorer
from app.services.control_engine import control_engine
from app.services.learning_store import learning_store
from app.services.regime_detector import regime_detector

router = APIRouter(prefix="/trade", tags=["trade"])


@router.post("", response_model=TradeOutcomeResponse)
def record_trade(payload: TradeOutcomeRequest, user: User = HighTrustUser) -> TradeOutcomeResponse:
    regime = payload.regime or regime_detector.detect(symbol=payload.symbol, timeframe="1d").regime
    response = learning_store.record_trade_outcome(
        symbol=payload.symbol,
        strategy=payload.strategy,
        regime=regime,
        entry_price=payload.entry_price,
        exit_price=payload.exit_price,
    )
    control_engine.update_balance(pnl=response.pnl)
    agent_scorer.invalidate(symbol=payload.symbol)
    return response
