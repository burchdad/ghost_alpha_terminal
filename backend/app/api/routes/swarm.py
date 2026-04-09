from fastapi import APIRouter

from app.models.schemas import SwarmResponse
from app.services.agent_manager import agent_manager
from app.services.capital_allocator import AllocationInput, capital_allocator
from app.services.consensus_engine import consensus_engine
from app.services.control_engine import control_engine
from app.services.explainability import build_explainability
from app.services.goal_engine import goal_engine
from app.services.kronos_service import kronos_service
from app.services.agent_scorer import agent_scorer
from app.services.learning_store import learning_store
from app.services.options_service import options_service
from app.services.portfolio_manager import portfolio_manager
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

    action_from_bias = {
        "BULLISH": "BUY",
        "BEARISH": "SELL",
        "NEUTRAL": "HOLD",
    }.get(swarm.consensus.final_bias, "HOLD")
    agreement = (
        sum(1 for item in outputs if item.bias == swarm.consensus.final_bias) / len(outputs)
        if outputs
        else 0.0
    )

    volatility_map = {
        "LOW": 0.012,
        "MEDIUM": 0.020,
        "HIGH": 0.035,
    }
    realized_volatility = volatility_map.get(forecast.volatility, 0.020)

    risk_level = "HIGH" if regime.regime == "HIGH_VOLATILITY" else "MEDIUM" if regime.regime == "RANGE_BOUND" else "LOW"
    portfolio_state = portfolio_manager.snapshot()
    control_state = control_engine.status()
    goal_pressure = goal_engine.current_pressure(
        current_capital=float(portfolio_state["account_balance"])
    )

    allocation = capital_allocator.compute(
        AllocationInput(
            account_balance=float(portfolio_state["account_balance"]),
            current_price=options_data.underlying_price,
            confidence=swarm.consensus.confidence,
            regime=regime.regime,
            risk_level=risk_level,
            agent_agreement=agreement,
            drawdown_pct=float(control_state["rolling_drawdown_pct"]),
            current_exposure_pct=float(portfolio_state["risk_exposure_pct"]),
            realized_volatility_pct=realized_volatility,
            goal_pressure_multiplier=goal_pressure,
        )
    )

    risk = risk_engine.evaluate_trade(
        entry_price=options_data.underlying_price,
        stop_loss_pct=allocation["stop_loss_pct"],
        take_profit_pct=0.03,
        confidence=swarm.consensus.confidence,
        max_loss_amount=allocation["max_risk_amount"],
        account_balance=float(portfolio_state["account_balance"]),
    )

    if action_from_bias != "HOLD" and not allocation["accepted"]:
        risk["risk_level"] = "HIGH"

    swarm = swarm.model_copy(
        update={
            "regime": regime.regime,
            "regime_confidence": regime.confidence,
            "position_size": allocation["recommended_qty"],
            "risk_level": risk["risk_level"],
            "expected_value": risk["expected_value"],
            "explainability": build_explainability(
                reasoning=(
                    f"Consensus={swarm.consensus.final_bias} ({swarm.consensus.confidence:.2f}), "
                    f"trade={swarm.recommended_trade}, allocation_accept={allocation['accepted']}."
                ),
                confidence=swarm.consensus.confidence,
                risk_level=risk["risk_level"],
                expected_value=risk["expected_value"],
                accepted=bool(allocation["accepted"]),
                safeguards=["risk_engine", "capital_allocator", "goal_pressure"],
                inputs={
                    "goal_pressure_multiplier": goal_pressure,
                    "realized_volatility_pct": realized_volatility,
                    "target_pct": allocation["target_pct"],
                },
            ),
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
