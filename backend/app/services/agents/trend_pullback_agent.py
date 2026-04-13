from __future__ import annotations

from app.models.schemas import AgentDecision, ForecastResponse, OptionsChainResponse


class TrendPullbackAgent:
    name = "trend_pullback_agent"

    def run(
        self,
        symbol: str,
        forecast: ForecastResponse,
        options_data: OptionsChainResponse,
        regime: str | None = None,
    ) -> AgentDecision:
        path = [float(v) for v in forecast.forecast_prices if isinstance(v, (int, float))]
        if len(path) < 4:
            return AgentDecision(
                agent_name=self.name,
                bias="NEUTRAL",
                confidence=0.55,
                suggested_strategy="WAIT",
                reasoning="Insufficient path depth for pullback confirmation.",
            )

        impulse = path[-1] - path[0]
        retrace = path[-1] - path[-3]

        if forecast.direction == "UP" and impulse > 0 and retrace < 0:
            confidence = 0.74 if regime == "TRENDING" else 0.66
            return AgentDecision(
                agent_name=self.name,
                bias="BULLISH",
                confidence=confidence,
                suggested_strategy="BUY_CALL_ON_PULLBACK",
                reasoning="Bullish impulse with short pullback suggests trend continuation entry.",
            )

        if forecast.direction == "DOWN" and impulse < 0 and retrace > 0:
            confidence = 0.74 if regime == "TRENDING" else 0.66
            return AgentDecision(
                agent_name=self.name,
                bias="BEARISH",
                confidence=confidence,
                suggested_strategy="BUY_PUT_ON_RALLY",
                reasoning="Bearish impulse with relief rally suggests continuation short entry.",
            )

        return AgentDecision(
            agent_name=self.name,
            bias="NEUTRAL",
            confidence=0.59,
            suggested_strategy="WAIT",
            reasoning="No clean pullback continuation structure.",
        )
