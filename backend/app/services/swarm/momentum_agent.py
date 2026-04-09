"""
MomentumAgent — execution-oriented swarm agent.

Strategy:
  - Measures short-term price momentum via a fast/slow EMA crossover.
  - Regime-aware: higher conviction in TRENDING, reduced in RANGE_BOUND.
  - BUY  when fast EMA crosses above slow EMA.
  - SELL when fast EMA crosses below slow EMA.
  - HOLD otherwise or when price history is insufficient.
"""
from __future__ import annotations

import numpy as np

from app.services.swarm.base_agent import MarketSnapshot, SwarmSignal, TradingAgent


class MomentumAgent(TradingAgent):
    name = "momentum_agent"

    FAST_PERIOD = 8
    SLOW_PERIOD = 21

    def __init__(self) -> None:
        self._snapshot: MarketSnapshot | None = None
        self._fast_ema: float = 0.0
        self._slow_ema: float = 0.0

    @staticmethod
    def _ema(prices: np.ndarray, period: int) -> float:
        """Compute the last EMA value for the given period."""
        if len(prices) < period:
            return float(prices[-1])
        k = 2.0 / (period + 1)
        ema = float(np.mean(prices[:period]))
        for p in prices[period:]:
            ema = p * k + ema * (1 - k)
        return ema

    def analyze_market(self, snapshot: MarketSnapshot) -> None:
        self._snapshot = snapshot
        prices = np.array(snapshot.close_prices, dtype=float)
        self._fast_ema = self._ema(prices, self.FAST_PERIOD)
        self._slow_ema = self._ema(prices, self.SLOW_PERIOD)
        spread = abs(self._fast_ema - self._slow_ema) / max(self._slow_ema, 1e-6)
        # base confidence from separation magnitude (capped 0.5–0.85)
        self.confidence_score = round(min(0.85, max(0.5, 0.5 + spread * 20)), 3)

        if snapshot.regime == "TRENDING":
            self.confidence_score = round(min(0.92, self.confidence_score + 0.07), 3)
        elif snapshot.regime == "RANGE_BOUND":
            self.confidence_score = round(max(0.45, self.confidence_score - 0.08), 3)

    def generate_signal(self) -> SwarmSignal:
        snap = self._snapshot
        if snap is None or len(snap.close_prices) < self.SLOW_PERIOD:
            return SwarmSignal(
                agent_name=self.name,
                action="HOLD",
                confidence=0.45,
                reasoning="Insufficient price history for EMA crossover.",
            )

        if self._fast_ema > self._slow_ema:
            return SwarmSignal(
                agent_name=self.name,
                action="BUY",
                confidence=self.confidence_score,
                reasoning=(
                    f"Fast EMA ({self._fast_ema:.2f}) above slow EMA ({self._slow_ema:.2f}). "
                    f"Bullish momentum — regime: {snap.regime}."
                ),
            )
        if self._fast_ema < self._slow_ema:
            return SwarmSignal(
                agent_name=self.name,
                action="SELL",
                confidence=self.confidence_score,
                reasoning=(
                    f"Fast EMA ({self._fast_ema:.2f}) below slow EMA ({self._slow_ema:.2f}). "
                    f"Bearish momentum — regime: {snap.regime}."
                ),
            )
        return SwarmSignal(
            agent_name=self.name,
            action="HOLD",
            confidence=0.5,
            reasoning="EMAs are equal — no directional edge.",
        )
