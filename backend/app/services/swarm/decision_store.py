"""
In-memory decision store for swarm cycle outputs.

Holds the last N AgentCycleRecord entries in a thread-safe deque
for immediate API consumption and future WebSocket streaming.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Literal

_DEFAULT_MAX = 200


@dataclass
class AgentCycleRecord:
    """Full audit record of one swarm decision cycle."""
    cycle_id: str
    symbol: str
    timestamp: datetime
    regime: str
    agent_signals: list[dict]          # one per agent {name, action, confidence, reasoning}
    final_action: Literal["BUY", "SELL", "HOLD"]
    final_confidence: float
    consensus_reasoning: str
    execution_submitted: bool          # True if sent to Alpaca
    execution_result: dict | None      # Alpaca order response or error dict
    vetoed: bool = False
    veto_reason: str = ""
    request_id: str = field(default="")  # X-Request-ID from our middleware
    allocation: dict | None = None
    outcome: dict | None = None
    agent_attribution: list[dict] = field(default_factory=list)
    settlement_applied: bool = False


class SwarmDecisionStore:
    def __init__(self, maxlen: int = _DEFAULT_MAX) -> None:
        self._records: deque[AgentCycleRecord] = deque(maxlen=maxlen)
        self._lock = threading.Lock()
        self._total_cycles: int = 0

    def append(self, record: AgentCycleRecord) -> None:
        with self._lock:
            self._records.append(record)
            self._total_cycles += 1

    def get_recent(self, n: int = 50) -> list[AgentCycleRecord]:
        with self._lock:
            return list(self._records)[-n:]

    def get_latest(self) -> AgentCycleRecord | None:
        with self._lock:
            return self._records[-1] if self._records else None

    def get_by_cycle_id(self, cycle_id: str) -> AgentCycleRecord | None:
        with self._lock:
            for record in reversed(self._records):
                if record.cycle_id == cycle_id:
                    return record
        return None

    def update_outcome(
        self,
        *,
        cycle_id: str,
        entry_price: float,
        exit_price: float,
    ) -> AgentCycleRecord | None:
        with self._lock:
            target: AgentCycleRecord | None = None
            for record in reversed(self._records):
                if record.cycle_id == cycle_id:
                    target = record
                    break

            if target is None:
                return None

            pnl = round(exit_price - entry_price, 6)
            if target.final_action == "SELL":
                pnl = round(-pnl, 6)

            outcome_label = "WIN" if pnl >= 0 else "LOSS"
            target.outcome = {
                "entry_price": entry_price,
                "exit_price": exit_price,
                "pnl": pnl,
                "outcome_label": outcome_label,
            }

            total_conf = sum(float(sig.get("confidence", 0.0)) for sig in target.agent_signals) or 1.0
            attributions: list[dict] = []
            for sig in target.agent_signals:
                prediction = sig.get("action", "HOLD")
                confidence = float(sig.get("confidence", 0.0))

                if target.final_action == "HOLD":
                    correct = prediction == "HOLD"
                elif outcome_label == "WIN":
                    correct = prediction == target.final_action
                else:
                    correct = prediction != target.final_action and prediction != "HOLD"

                signed = 1.0 if correct else -1.0
                contribution = round((abs(pnl) * confidence / total_conf) * signed, 6)

                attributions.append(
                    {
                        "agent_name": sig.get("agent_name", "unknown"),
                        "prediction": prediction,
                        "confidence": confidence,
                        "correct": bool(correct),
                        "pnl_contribution": float(contribution),
                    }
                )

            target.agent_attribution = attributions

            # Feed settled outcomes into the dynamic weight engine
            # Import lazily to avoid circular import at module load time
            from app.services.swarm.weight_engine import dynamic_weight_engine  # noqa: PLC0415
            from app.services.control_engine import control_engine  # noqa: PLC0415
            from app.services.execution_journal import execution_journal  # noqa: PLC0415
            from app.services.portfolio_manager import portfolio_manager  # noqa: PLC0415

            dynamic_weight_engine.record_outcome(
                cycle_id=cycle_id,
                regime=target.regime,
                attribution=attributions,
            )

            execution_journal.update_outcome(
                cycle_id,
                outcome_label=outcome_label,
                pnl=pnl,
            )

            if (
                target.execution_result
                and not target.settlement_applied
                and target.final_action != "HOLD"
                and target.execution_result.get("track_position")
            ):
                portfolio_manager.close_position(cycle_id=cycle_id, pnl=pnl)
                control_engine.update_balance(pnl=pnl)
                target.settlement_applied = True

            return target

    @property
    def total_cycles(self) -> int:
        with self._lock:
            return self._total_cycles


swarm_decision_store = SwarmDecisionStore()
