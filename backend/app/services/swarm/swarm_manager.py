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

from app.services.capital_allocator import AllocationInput, capital_allocator
from app.services.control_engine import control_engine
from app.services.execution_journal import execution_journal
from app.services.portfolio_manager import portfolio_manager
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
        cycle_id = uuid.uuid4().hex

        # 1. Collect signals
        signals: list[SwarmSignal] = [agent.run(snapshot) for agent in self._signal_agents]

        # 2. Weighted vote
        final_action, final_confidence, consensus_reasoning = self._aggregate(signals, snapshot)
        risk_level = self._risk_level(snapshot.regime, final_confidence)
        agreement = self._agent_agreement(signals, final_action)

        # 3. Risk veto
        self._risk.analyze_market(snapshot)
        vetoed, veto_reason = self._risk.veto(final_action, final_confidence)
        if vetoed:
            final_action = "HOLD"
            consensus_reasoning = veto_reason

        portfolio_state = portfolio_manager.snapshot()
        control_state = control_engine.status()
        allocation = capital_allocator.compute(
            AllocationInput(
                account_balance=float(portfolio_state["account_balance"]),
                current_price=snapshot.current_price,
                confidence=final_confidence,
                regime=regime,
                risk_level=risk_level,
                agent_agreement=agreement,
                drawdown_pct=float(control_state["rolling_drawdown_pct"]),
                current_exposure_pct=float(portfolio_state["risk_exposure_pct"]),
            )
        )

        if final_action != "HOLD" and allocation["accepted"]:
            can_open, open_reason = portfolio_manager.can_open_position(
                symbol=symbol.upper(),
                strategy="SWARM_MARKET",
                notional=float(allocation["recommended_notional"]),
            )
            if not can_open:
                allocation["accepted"] = False
                allocation["reason"] = open_reason

        # 4. Submit to Alpaca / simulation
        if final_action != "HOLD" and not allocation["accepted"]:
            exec_result = {
                "submitted": False,
                "action": final_action,
                "order_id": None,
                "error": None,
                "mode": execution_bridge.get_mode(),
                "track_position": False,
                "reason": allocation["reason"],
            }
        else:
            exec_result = execution_bridge.submit(
                symbol=symbol.upper(),
                action=final_action,
                qty=allocation["recommended_qty"] if allocation["accepted"] else default_qty,
                confidence=final_confidence,
                client_order_id=f"swarm-{symbol.upper()}-{uuid.uuid4().hex[:12]}",
            )

        if final_action != "HOLD" and allocation["accepted"] and exec_result.get("track_position"):
            opened = portfolio_manager.open_position(
                cycle_id=cycle_id,
                symbol=symbol.upper(),
                strategy="SWARM_MARKET",
                side="LONG" if final_action == "BUY" else "SHORT",
                entry_price=snapshot.current_price,
                units=allocation["recommended_qty"],
            )
            if not opened.get("accepted", False):
                exec_result = {
                    **exec_result,
                    "submitted": False,
                    "track_position": False,
                    "reason": opened.get("reason", "Portfolio rejected position."),
                }

        # 5. Build and store record
        record = AgentCycleRecord(
            cycle_id=cycle_id,
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
            allocation=allocation,
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

        execution_journal.append(
            cycle_id=cycle_id,
            symbol=symbol.upper(),
            regime=regime,
            action=final_action,
            strategy="SWARM_MARKET",
            confidence=round(final_confidence, 3),
            risk_level=risk_level,
            allocation_pct=float(allocation["target_pct"]),
            qty=float(allocation["recommended_qty"]),
            notional=float(allocation["recommended_notional"]),
            mode=exec_result.get("mode", execution_bridge.get_mode()),
            submitted=bool(exec_result.get("submitted", False)),
            order_id=exec_result.get("order_id"),
            reason=exec_result.get("reason", allocation.get("reason", "")),
            error=exec_result.get("error"),
        )

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

    def _risk_level(self, regime: str, confidence: float) -> str:
        if regime == "HIGH_VOLATILITY" or confidence < 0.58:
            return "HIGH"
        if regime == "RANGE_BOUND" or confidence < 0.70:
            return "MEDIUM"
        return "LOW"

    def _agent_agreement(self, signals: list[SwarmSignal], final_action: str) -> float:
        if not signals:
            return 0.0
        agreeing = sum(1 for sig in signals if sig.action == final_action)
        return agreeing / len(signals)

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
        "final_confidence": _json_safe(r.final_confidence),
        "vetoed": _json_safe(r.vetoed),
        "veto_reason": r.veto_reason,
        "execution_submitted": _json_safe(r.execution_submitted),
        "allocation": _json_safe(r.allocation),
        "agent_signals": _json_safe(r.agent_signals),
        "outcome": _json_safe(r.outcome),
        "agent_attribution": _json_safe(r.agent_attribution),
    }


def _json_safe(value):
    if isinstance(value, dict):
        return {k: _json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_json_safe(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            return value
    return value


swarm_manager = AgentSwarmManager()
