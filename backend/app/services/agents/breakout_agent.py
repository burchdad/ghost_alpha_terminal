from __future__ import annotations

from app.models.schemas import AgentDecision, ForecastResponse, OptionsChainResponse


class BreakoutAgent:
    name = "breakout_agent"

    def run(
        self,
        symbol: str,
        forecast: ForecastResponse,
        options_data: OptionsChainResponse,
        regime: str | None = None,
    ) -> AgentDecision:
        path = [float(v) for v in forecast.forecast_prices if isinstance(v, (int, float))]
        if len(path) < 5:
            return AgentDecision(
                agent_name=self.name,
                bias="NEUTRAL",
                confidence=0.54,
                suggested_strategy="WAIT",
                reasoning="Insufficient projected path for breakout detection.",
            )

        recent = path[-5:]
        last = recent[-1]
        prior_high = max(recent[:-1])
        prior_low = min(recent[:-1])

        if last > prior_high * 1.004:
            confidence = 0.79 if regime in {"TRENDING", "HIGH_VOLATILITY"} else 0.7
            return AgentDecision(
                agent_name=self.name,
                bias="BULLISH",
                confidence=confidence,
                suggested_strategy="BREAKOUT_CALL_DEBIT",
                reasoning="Projected price clears recent resistance with expansion profile.",
            )

        if last < prior_low * 0.996:
            confidence = 0.79 if regime in {"TRENDING", "HIGH_VOLATILITY"} else 0.7
            return AgentDecision(
                agent_name=self.name,
                bias="BEARISH",
                confidence=confidence,
                suggested_strategy="BREAKDOWN_PUT_DEBIT",
                reasoning="Projected price breaks recent support with downside expansion profile.",
            )

        return AgentDecision(
            agent_name=self.name,
            bias="NEUTRAL",
            confidence=0.58,
            suggested_strategy="WAIT",
            reasoning="No projected breakout from local range.",
        )
