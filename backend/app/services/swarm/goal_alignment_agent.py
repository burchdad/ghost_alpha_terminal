from __future__ import annotations

from app.services.goal_engine import goal_engine
from app.services.portfolio_manager import portfolio_manager
from app.services.swarm.base_agent import MarketSnapshot, SwarmSignal, TradingAgent


class GoalAlignmentAgent(TradingAgent):
    """Agent that adjusts directional aggression based on goal pressure and trend slope."""

    name = "goal_alignment_agent"

    def __init__(self) -> None:
        self._snapshot: MarketSnapshot | None = None
        self._pressure: float = 1.0
        self._trajectory_gap: float = 0.0
        self._trend: float = 0.0

    def analyze_market(self, snapshot: MarketSnapshot) -> None:
        self._snapshot = snapshot
        portfolio = portfolio_manager.snapshot()
        goal_status = goal_engine.status(current_capital=float(portfolio["account_balance"]))
        self._pressure = float(goal_status.get("goal_pressure_multiplier", 1.0))
        self._trajectory_gap = float(goal_status.get("trajectory_gap_pct", 0.0))

        prices = snapshot.close_prices
        if len(prices) >= 8 and prices[0] > 0:
            self._trend = (prices[-1] / prices[-8]) - 1.0
        elif len(prices) >= 2 and prices[-2] > 0:
            self._trend = (prices[-1] / prices[-2]) - 1.0
        else:
            self._trend = 0.0

        base_conf = 0.48 + min(abs(self._trend) * 6, 0.25)
        pressure_boost = max(0.0, self._pressure - 1.0) * 0.08
        self.confidence_score = round(min(0.92, max(0.45, base_conf + pressure_boost)), 3)

    def generate_signal(self) -> SwarmSignal:
        if self._snapshot is None:
            return SwarmSignal(
                agent_name=self.name,
                action="HOLD",
                confidence=0.45,
                reasoning="No snapshot available for goal-alignment assessment.",
            )

        if self._pressure <= 1.0:
            return SwarmSignal(
                agent_name=self.name,
                action="HOLD",
                confidence=0.5,
                reasoning=(
                    f"Goal pressure neutral ({self._pressure:.2f}); no aggression override required."
                ),
            )

        if self._trend > 0.003:
            action = "BUY"
            directional_reason = "positive short-term trend supports upside pursuit"
        elif self._trend < -0.003:
            action = "SELL"
            directional_reason = "negative short-term trend supports downside hedge/opportunity"
        else:
            action = "HOLD"
            directional_reason = "trend too weak for pressure-based directional override"

        return SwarmSignal(
            agent_name=self.name,
            action=action,
            confidence=self.confidence_score,
            reasoning=(
                f"Goal pressure={self._pressure:.2f}, trajectory_gap={self._trajectory_gap:.2%}, "
                f"trend={self._trend:.3%}; {directional_reason}."
            ),
        )
