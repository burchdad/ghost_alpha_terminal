from __future__ import annotations

from app.models.schemas import AgentDecision, ForecastResponse, OptionsChainResponse


class MomentumAgent:
    name = "momentum_agent"

    def run(
        self,
        symbol: str,
        forecast: ForecastResponse,
        options_data: OptionsChainResponse,
        regime: str | None = None,
    ) -> AgentDecision:
        bias = "NEUTRAL"
        strategy = "WAIT"
        reasoning = "Momentum is mixed."
        confidence = 0.56

        if forecast.direction == "UP" and forecast.confidence > 0.6:
            bias = "BULLISH"
            strategy = "BUY_CALL"
            confidence = min(0.9, forecast.confidence + 0.08)
            reasoning = "Positive trend and forecast alignment support upside continuation."
        elif forecast.direction == "DOWN" and forecast.confidence > 0.6:
            bias = "BEARISH"
            strategy = "BUY_PUT"
            confidence = min(0.9, forecast.confidence + 0.08)
            reasoning = "Negative trend and forecast alignment support downside continuation."

        if regime == "TRENDING" and bias != "NEUTRAL":
            confidence = min(0.95, confidence + 0.06)
            reasoning = f"{reasoning} Trend regime increases momentum reliability."
        elif regime == "RANGE_BOUND" and bias != "NEUTRAL":
            confidence = max(0.5, confidence - 0.08)
            reasoning = f"{reasoning} Range-bound regime weakens momentum continuation."

        return AgentDecision(
            agent_name=self.name,
            bias=bias,
            confidence=round(confidence, 3),
            suggested_strategy=strategy,
            reasoning=reasoning,
        )
