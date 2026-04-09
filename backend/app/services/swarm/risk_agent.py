"""
RiskAgent — meta-agent that can override or veto swarm decisions.

This agent does NOT generate independent buy/sell signals.
Instead, it:
  - Measures current volatility (ATR-like)
  - Checks volume anomalies
  - Audits the risk posture of a proposed consensus action
  - Can return HOLD to veto a trade that exceeds volatility thresholds

The AgentSwarmManager calls `veto()` after collecting all other
signals and before forming the final consensus, giving RiskAgent
override authority.
"""
from __future__ import annotations

import numpy as np

from app.services.swarm.base_agent import MarketSnapshot, SwarmSignal, TradingAgent

# Veto thresholds
_VOL_VETO_THRESHOLD = 0.05      # realised vol (stdev of returns) > 5% → veto
_VOLUME_SPIKE_MULT = 3.0        # volume > 3× average → suspicious, reduce confidence


class RiskAgent(TradingAgent):
    name = "risk_agent"

    def __init__(self) -> None:
        self._snapshot: MarketSnapshot | None = None
        self._realised_vol: float = 0.0
        self._volume_ratio: float = 1.0
        self._veto_reason: str = ""

    def analyze_market(self, snapshot: MarketSnapshot) -> None:
        self._snapshot = snapshot
        prices = np.array(snapshot.close_prices, dtype=float)

        if len(prices) >= 2:
            returns = np.diff(prices) / np.maximum(prices[:-1], 1e-6)
            self._realised_vol = float(np.std(returns, ddof=1))
        else:
            self._realised_vol = 0.0

        volumes = np.array(snapshot.volumes, dtype=float)
        avg_vol = float(np.mean(volumes[:-1])) if len(volumes) > 1 else float(volumes[-1])
        current_vol = float(volumes[-1]) if len(volumes) > 0 else avg_vol
        self._volume_ratio = current_vol / max(avg_vol, 1.0)

        # confidence = inverse of normalised vol; higher vol → lower confidence
        self.confidence_score = round(max(0.3, min(0.9, 1.0 - self._realised_vol * 10)), 3)

        if snapshot.regime == "HIGH_VOLATILITY":
            self.confidence_score = round(max(0.3, self.confidence_score - 0.1), 3)

    def generate_signal(self) -> SwarmSignal:
        """
        Risk agent always returns a risk-status signal, not a directional one.
        Use `veto()` for override logic.
        """
        snap = self._snapshot
        regime = snap.regime if snap else "UNKNOWN"
        return SwarmSignal(
            agent_name=self.name,
            action="HOLD",
            confidence=self.confidence_score,
            reasoning=(
                f"Risk monitor: realised_vol={self._realised_vol:.4f}, "
                f"volume_ratio={self._volume_ratio:.2f}x, regime={regime}."
            ),
        )

    def veto(self, proposed_action: str, consensus_confidence: float) -> tuple[bool, str]:
        """
        Return (True, reason) if the RiskAgent vetoes the proposed action.
        Called by AgentSwarmManager before final decision.
        """
        if self._realised_vol > _VOL_VETO_THRESHOLD:
            return True, (
                f"Volatility veto: realised_vol={self._realised_vol:.4f} exceeds "
                f"threshold {_VOL_VETO_THRESHOLD:.2f}. Trade blocked by risk agent."
            )

        snap = self._snapshot
        if snap and snap.regime == "HIGH_VOLATILITY" and proposed_action != "HOLD":
            if consensus_confidence < 0.72:
                return True, (
                    f"HIGH_VOLATILITY regime + low consensus confidence "
                    f"({consensus_confidence:.2f} < 0.72). Risk agent forcing HOLD."
                )

        if self._volume_ratio > _VOLUME_SPIKE_MULT and proposed_action != "HOLD":
            return True, (
                f"Volume spike ({self._volume_ratio:.1f}× average). "
                "Unusual activity detected — trade blocked by risk agent."
            )

        return False, ""
