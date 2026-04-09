"""
AgentSwarmManager — the orchestrator.

Execution flow per cycle:
  1. Build MarketSnapshot from historical data or live feed
  2. Run every non-Risk agent → collect SwarmSignals
  3. Aggregate signals via weighted confidence voting
  4. Ask RiskAgent to veto if risk conditions are breached
  5. Submit final action to Alpaca via the execution bridge (paper only)
  6. Persist full AgentCycleRecord to SwarmDecisionStore

The manager is a singleton (swarm_manager) imported by the route layer.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from app.services.swarm.base_agent import MarketSnapshot, SwarmSignal
from app.services.swarm.decision_store import AgentCycleRecord, swarm_decision_store
from app.services.swarm.execution_bridge import execution_bridge
from app.services.swarm.mean_reversion_agent import MeanReversionAgent
from app.services.swarm.momentum_agent import MomentumAgent
from app.services.swarm.risk_agent import RiskAgent
from app.services.swarm.sentiment_agent import SentimentAgent
from app.services.swarm.weight_engine import dynamic_weight_engine

logger = logging.getLogger(__name__)

_ACTION_SCORE: dict[str, float] = {"BUY": 1.0, "HOLD": 0.0, "SELL": -1.0}


class AgentSwarmManager:
    def __init__(self) -> None:
        self._momentum = MomentumAgent()
        self._mean_reversion = MeanReversionAgent()
        self._sentiment = SentimentAgent()
        self._risk = RiskAgent()
        self._signal_agents = [self._momentum, self._mean_reversion, self._sentiment]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_cycle(
        self,
        symbol: str,
        close_prices: list[float],
        volumes: list[float],
        *,
        regime: Literal["TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY"] = "RANGE_BOUND",
        regime_confidence: float = 0.5,
        default_qty: float = 1.0,
    ) -> AgentCycleRecord:
        """Run a full swarm decision cycle and return the audit record."""
        if not close_prices:
            raise ValueError("close_prices must not be empty")

        snapshot = MarketSnapshot(
            symbol=symbol.upper(),
            close_prices=close_prices,
            volumes=volumes,
            current_price=close_prices[-1],
            regime=regime,
            regime_confidence=regime_confidence,
        )

        # 1. Collect signals
        signals: list[SwarmSignal] = [agent.run(snapshot) for agent in self._signal_agents]

        # 2. Weighted vote
        final_action, final_confidence, consensus_reasoning = self._aggregate(signals, snapshot)

        # 3. Risk veto
        self._risk.analyze_market(snapshot)
        vetoed, veto_reason = self._risk.veto(final_action, final_confidence)
        if vetoed:
            final_action = "HOLD"
            consensus_reasoning = veto_reason

        # 4. Submit to Alpaca (paper)
        exec_result = execution_bridge.submit(
            symbol=symbol.upper(),
            action=final_action,
            qty=default_qty,
            confidence=final_confidence,
        )

        # 5. Build and store record
        record = AgentCycleRecord(
            cycle_id=uuid.uuid4().hex,
            symbol=symbol.upper(),
            timestamp=datetime.now(tz=timezone.utc),
            regime=regime,
            agent_signals=[
                {
                    "agent_name": s.agent_name,
                    "action": s.action,
                    "confidence": s.confidence,
                    "reasoning": s.reasoning,
                }
                for s in signals
            ],
            final_action=final_action,
            final_confidence=round(final_confidence, 3),
            consensus_reasoning=consensus_reasoning,
            execution_submitted=exec_result.get("submitted", False),
            execution_result=exec_result,
            vetoed=vetoed,
            veto_reason=veto_reason,
            agent_attribution=[
                {
                    "agent_name": s.agent_name,
                    "prediction": s.action,
                    "confidence": s.confidence,
                    "correct": None,
                    "pnl_contribution": None,
                }
                for s in signals
            ],
        )
        swarm_decision_store.append(record)

        logger.info(
            "swarm_cycle symbol=%s action=%s confidence=%.3f vetoed=%s submitted=%s",
            symbol.upper(),
            final_action,
            final_confidence,
            vetoed,
            record.execution_submitted,
        )
        return record

    def status(self) -> dict:
        """Return the current health / configuration of the swarm."""
        return {
            "agents": [
                {"name": a.name, "confidence_score": a.confidence_score}
                for a in [*self._signal_agents, self._risk]
            ],
            "total_cycles": swarm_decision_store.total_cycles,
            "execution_mode": execution_bridge.get_mode(),
            "latest_decision": _record_to_dict(swarm_decision_store.get_latest()),
            "current_weights": dynamic_weight_engine.get_all_regime_weights(),
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _aggregate(
        self,
        signals: list[SwarmSignal],
        snapshot: MarketSnapshot,
    ) -> tuple[str, float, str]:
        """
        Weighted-confidence majority vote using dynamic per-regime weights.
        Returns (final_action, confidence, reasoning).
        """
        # Fetch current dynamic weights for the active market regime
        active_weights = dynamic_weight_engine.compute_weights(snapshot.regime)

        total_weight = 0.0
        weighted_score = 0.0
        reasoning_parts: list[str] = []

        for sig in signals:
            w = active_weights.get(sig.agent_name, 1.0 / 3)
            vote_score = _ACTION_SCORE.get(sig.action, 0.0)
            weighted_score += vote_score * sig.confidence * w
            total_weight += w
            reasoning_parts.append(
                f"{sig.agent_name}(w={w:.2f}): {sig.action} ({sig.confidence:.2f})"
            )

        normalised = weighted_score / max(total_weight, 1e-6)

        if normalised > 0.15:
            action: str = "BUY"
        elif normalised < -0.15:
            action = "SELL"
        else:
            action = "HOLD"

        confidence = round(min(0.95, max(0.45, abs(normalised) * 0.6 + 0.4)), 3)
        weight_summary = " | ".join(
            f"{a.split('_')[0]}={w:.2f}" for a, w in active_weights.items()
        )
        reasoning = (
            f"Weighted consensus score={normalised:.3f} [weights: {weight_summary}]. "
            + " | ".join(reasoning_parts)
        )

        logger.info(
            "swarm_aggregate regime=%s weights=%s score=%.3f action=%s",
            snapshot.regime,
            active_weights,
            normalised,
            action,
        )
        return action, confidence, reasoning


def _record_to_dict(r: AgentCycleRecord | None) -> dict | None:
    if r is None:
        return None
    return {
        "cycle_id": r.cycle_id,
        "symbol": r.symbol,
        "timestamp": r.timestamp.isoformat(),
        "regime": r.regime,
        "final_action": r.final_action,
        "final_confidence": r.final_confidence,
        "vetoed": r.vetoed,
        "veto_reason": r.veto_reason,
        "execution_submitted": r.execution_submitted,
        "agent_signals": r.agent_signals,
        "outcome": r.outcome,
        "agent_attribution": r.agent_attribution,
    }


swarm_manager = AgentSwarmManager()
