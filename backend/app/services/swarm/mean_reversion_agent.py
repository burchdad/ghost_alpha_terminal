"""
MeanReversionAgent — execution-oriented swarm agent.

Strategy:
  - Uses Bollinger Bands (20-period SMA ± 2σ).
  - BUY  when price touches / breaks below lower band (oversold).
  - SELL when price touches / breaks above upper band (overbought).
  - HOLD when price is within bands.
  - Regime-aware: higher conviction in RANGE_BOUND, reduced in TRENDING.
"""
from __future__ import annotations

import numpy as np

from app.services.swarm.base_agent import MarketSnapshot, SwarmSignal, TradingAgent


class MeanReversionAgent(TradingAgent):
    name = "mean_reversion_agent"

    PERIOD = 20
    STD_MULT = 2.0

    def __init__(self) -> None:
        self._snapshot: MarketSnapshot | None = None
        self._upper: float = 0.0
        self._lower: float = 0.0
        self._mid: float = 0.0
        self._z_score: float = 0.0

    def analyze_market(self, snapshot: MarketSnapshot) -> None:
        self._snapshot = snapshot
        prices = np.array(snapshot.close_prices, dtype=float)
        window = prices[-self.PERIOD:] if len(prices) >= self.PERIOD else prices

        self._mid = float(np.mean(window))
        std = float(np.std(window, ddof=1)) if len(window) > 1 else 0.0
        self._upper = self._mid + self.STD_MULT * std
        self._lower = self._mid - self.STD_MULT * std

        current = snapshot.current_price
        self._z_score = (current - self._mid) / max(std, 1e-6) if std > 0 else 0.0

        # confidence from z-score magnitude (0.5 → 0.9)
        self.confidence_score = round(min(0.9, 0.5 + abs(self._z_score) * 0.12), 3)
        if snapshot.regime == "RANGE_BOUND":
            self.confidence_score = round(min(0.92, self.confidence_score + 0.06), 3)
        elif snapshot.regime == "TRENDING":
            self.confidence_score = round(max(0.4, self.confidence_score - 0.1), 3)

    def generate_signal(self) -> SwarmSignal:
        snap = self._snapshot
        if snap is None:
            return SwarmSignal(
                agent_name=self.name,
                action="HOLD",
                confidence=0.45,
                reasoning="No market data available.",
            )

        cp = snap.current_price
        if cp <= self._lower:
            return SwarmSignal(
                agent_name=self.name,
                action="BUY",
                confidence=self.confidence_score,
                reasoning=(
                    f"Price {cp:.2f} at/below lower Bollinger band {self._lower:.2f} "
                    f"(z={self._z_score:.2f}). Oversold — expect mean reversion up."
                ),
            )
        if cp >= self._upper:
            return SwarmSignal(
                agent_name=self.name,
                action="SELL",
                confidence=self.confidence_score,
                reasoning=(
                    f"Price {cp:.2f} at/above upper Bollinger band {self._upper:.2f} "
                    f"(z={self._z_score:.2f}). Overbought — expect mean reversion down."
                ),
            )
        return SwarmSignal(
            agent_name=self.name,
            action="HOLD",
            confidence=round(max(0.45, 0.6 - abs(self._z_score) * 0.05), 3),
            reasoning=(
                f"Price {cp:.2f} within Bollinger bands "
                f"[{self._lower:.2f} – {self._upper:.2f}]. No edge."
            ),
        )
