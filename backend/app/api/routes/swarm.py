from fastapi import APIRouter

from app.models.schemas import SwarmResponse
from app.services.agent_manager import agent_manager
from app.services.consensus_engine import consensus_engine
from app.services.kronos_service import kronos_service
from app.services.agent_scorer import agent_scorer
from app.services.learning_store import learning_store
from app.services.options_service import options_service
from app.services.position_sizer import position_sizer
from app.services.regime_detector import regime_detector
from app.services.risk_engine import risk_engine
from app.services.signal_engine import signal_engine

router = APIRouter(prefix="/swarm", tags=["swarm"])


@router.get("/{symbol}", response_model=SwarmResponse)
def get_swarm(symbol: str) -> SwarmResponse:
    forecast = kronos_service.generate_forecast(symbol=symbol, timeframe="1d")
    regime = regime_detector.detect(symbol=symbol, timeframe="1d")
    options_data = options_service.get_options_chain(symbol=symbol)
    outputs = agent_manager.run_agents(symbol=symbol, forecast=forecast, options_data=options_data, regime=regime.regime)
    signal = signal_engine.generate_signal(symbol=symbol, forecast=forecast, options_data=options_data)
    swarm = consensus_engine.generate_consensus(symbol=symbol, outputs=outputs)

    sizing = position_sizer.calculate_position_size(
        account_balance=100000,
        risk_per_trade=0.01,
        stop_loss_pct=0.02,
        entry_price=options_data.underlying_price,
    )
    risk = risk_engine.evaluate_trade(
        entry_price=options_data.underlying_price,
        stop_loss_pct=0.02,
        take_profit_pct=0.03,
        confidence=swarm.consensus.confidence,
        max_loss_amount=sizing["max_loss_amount"],
        account_balance=100000,
    )
    swarm = swarm.model_copy(
        update={
            "regime": regime.regime,
            "regime_confidence": regime.confidence,
            "position_size": sizing["position_size"],
            "risk_level": risk["risk_level"],
            "expected_value": risk["expected_value"],
        }
    )

    learning_store.save_swarm_snapshot(
        symbol=symbol,
        forecast=forecast,
        signal=signal,
        swarm=swarm,
        agent_outputs=outputs,
    )
    agent_scorer.invalidate(symbol=symbol)
    return swarm
