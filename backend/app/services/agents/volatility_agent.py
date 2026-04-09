from __future__ import annotations

from app.models.schemas import AgentDecision, ForecastResponse, OptionsChainResponse


class VolatilityAgent:
    name = "volatility_agent"

    def run(
        self,
        symbol: str,
        forecast: ForecastResponse,
        options_data: OptionsChainResponse,
        regime: str | None = None,
    ) -> AgentDecision:
        if forecast.volatility == "HIGH" or regime == "HIGH_VOLATILITY":
            return AgentDecision(
                agent_name=self.name,
                bias="NEUTRAL",
                confidence=0.8,
                suggested_strategy="STRADDLE",
                reasoning="High volatility regime supports long-volatility structures.",
            )

        if forecast.volatility == "LOW":
            return AgentDecision(
                agent_name=self.name,
                bias="NEUTRAL",
                confidence=0.67,
                suggested_strategy="IRON_CONDOR",
                reasoning="Low realized regime often rewards premium-selling range structures.",
            )

        return AgentDecision(
            agent_name=self.name,
            bias="NEUTRAL",
            confidence=0.58,
            suggested_strategy="CALENDAR_SPREAD",
            reasoning="Medium volatility regime favors balanced vega exposure.",
        )
