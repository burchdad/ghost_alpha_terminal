"""
DynamicWeightEngine — self-adjusting agent influence calculator.

Replaces the static _AGENT_WEIGHTS dict in swarm_manager with weights
that evolve based on real settled outcomes.

Scoring factors per agent × regime bucket (exponential decay applied):
  - accuracy_term   : (1.0 if correct else -0.5) × confidence
  - pnl_term        : tanh(pnl_contribution × 10)  → bounded [-1, +1]
  - combined score  : 0.6 × accuracy_term + 0.4 × pnl_term

Weights are EMA-smoothed (alpha=0.3) then normalised to sum=1.0
with a hard floor (5%) and ceiling (70%) to prevent collapse.
"""
from __future__ import annotations

import math
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

AGENTS = ("momentum_agent", "mean_reversion_agent", "sentiment_agent")
REGIMES: tuple[str, ...] = ("TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY")

_DEFAULT_WEIGHT: float = round(1.0 / len(AGENTS), 6)
_DECAY_ALPHA: float = 0.85       # per-observation exponential decay
_EMA_ALPHA: float = 0.30         # smoothing factor for published weights
_WINDOW: int = 50                # max stored records per (agent, regime)
_FLOOR: float = 0.05             # minimum weight any single agent can hold
_CEIL: float = 0.70              # maximum weight any single agent can hold


@dataclass
class _PerfRecord:
    correct: bool
    pnl_contribution: float
    confidence: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


@dataclass
class WeightSnapshot:
    """Weight distribution captured after a settled outcome."""
    cycle_id: str
    timestamp: datetime
    regime: str
    weights: dict[str, float]     # agent_name → normalised weight
    raw_scores: dict[str, float]  # agent_name → pre-normalisation score


class DynamicWeightEngine:
    """
    Computes dynamic per-agent weights from settled trade outcomes.

    Thread-safe singleton — call record_outcome() after each
    update_outcome() call in the decision store, then fetch
    compute_weights(regime) inside _aggregate() of the swarm manager.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # _history[agent][regime] = list of PerfRecords (oldest first)
        self._history: dict[str, dict[str, list[_PerfRecord]]] = {
            agent: {regime: [] for regime in REGIMES}
            for agent in AGENTS
        }
        # EMA-smoothed current weights per (agent, regime)
        self._ema: dict[str, dict[str, float]] = {
            agent: {regime: _DEFAULT_WEIGHT for regime in REGIMES}
            for agent in AGENTS
        }
        # Weight snapshots for visualisation (capped at 500)
        self._snapshots: list[WeightSnapshot] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def record_outcome(
        self,
        cycle_id: str,
        regime: str,
        attribution: list[dict],
    ) -> None:
        """
        Ingest settled attribution records and update EMA weights.
        Called by SwarmDecisionStore.update_outcome().
        """
        if regime not in REGIMES:
            regime = "RANGE_BOUND"

        with self._lock:
            updated_agents: set[str] = set()

            for attr in attribution:
                agent = attr.get("agent_name", "")
                if agent not in AGENTS:
                    continue
                rec = _PerfRecord(
                    correct=bool(attr.get("correct", False)),
                    pnl_contribution=float(attr.get("pnl_contribution") or 0.0),
                    confidence=float(attr.get("confidence", 0.5)),
                )
                bucket = self._history[agent][regime]
                bucket.append(rec)
                if len(bucket) > _WINDOW:
                    bucket.pop(0)
                updated_agents.add(agent)

            if not updated_agents:
                return

            # Recompute EMA weights for this regime
            raw = self._raw_scores(regime)
            normed = self._normalise(raw)
            for agent in AGENTS:
                prev = self._ema[agent][regime]
                self._ema[agent][regime] = round(
                    _EMA_ALPHA * normed[agent] + (1.0 - _EMA_ALPHA) * prev, 6
                )

            snap = WeightSnapshot(
                cycle_id=cycle_id,
                timestamp=datetime.now(tz=timezone.utc),
                regime=regime,
                weights={a: self._ema[a][regime] for a in AGENTS},
                raw_scores=raw,
            )
            self._snapshots.append(snap)
            if len(self._snapshots) > 500:
                self._snapshots.pop(0)

    def compute_weights(self, regime: str) -> dict[str, float]:
        """Return current normalised EMA weights for the given regime."""
        if regime not in REGIMES:
            regime = "RANGE_BOUND"
        with self._lock:
            return {a: self._ema[a][regime] for a in AGENTS}

    def get_weight_history(self, n: int = 100) -> list[WeightSnapshot]:
        """Return last n weight snapshots in chronological order."""
        with self._lock:
            return list(self._snapshots[-n:])

    def get_all_regime_weights(self) -> dict[str, dict[str, float]]:
        """Return current EMA weights for every regime."""
        with self._lock:
            return {
                regime: {a: self._ema[a][regime] for a in AGENTS}
                for regime in REGIMES
            }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _raw_scores(self, regime: str) -> dict[str, float]:
        """Compute decay-weighted performance score per agent for a regime."""
        scores: dict[str, float] = {}
        for agent in AGENTS:
            bucket = self._history[agent][regime]
            if not bucket:
                scores[agent] = 0.0
                continue
            score = 0.0
            total_decay = 0.0
            for i, rec in enumerate(reversed(bucket)):
                decay = _DECAY_ALPHA ** i
                accuracy_term = (1.0 if rec.correct else -0.5) * rec.confidence
                pnl_term = math.tanh(rec.pnl_contribution * 10.0)
                combined = 0.6 * accuracy_term + 0.4 * pnl_term
                score += combined * decay
                total_decay += decay
            scores[agent] = score / max(total_decay, 1e-9)
        return scores

    def _normalise(self, raw: dict[str, float]) -> dict[str, float]:
        """
        Shift-positive → normalise → clamp [_FLOOR, _CEIL] → re-normalise.
        Guarantees all weights sum to 1.0 and no agent is locked out.
        """
        min_score = min(raw.values())
        shifted = {a: v - min_score + 1e-6 for a, v in raw.items()}
        total = sum(shifted.values())
        normed = {a: v / total for a, v in shifted.items()}
        clamped = {a: max(_FLOOR, min(_CEIL, v)) for a, v in normed.items()}
        total2 = sum(clamped.values())
        return {a: round(v / total2, 6) for a, v in clamped.items()}


# Singleton — shared across modules
dynamic_weight_engine = DynamicWeightEngine()
