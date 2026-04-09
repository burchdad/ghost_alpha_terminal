from __future__ import annotations

import numpy as np

from app.models.schemas import AgentDecision, ForecastResponse, OptionsChainResponse


class MeanReversionAgent:
    name = "mean_reversion_agent"

    def run(
        self,
        symbol: str,
        forecast: ForecastResponse,
        options_data: OptionsChainResponse,
        regime: str | None = None,
    ) -> AgentDecision:
        path = np.array(forecast.forecast_prices, dtype=float)
        if len(path) < 2:
            return AgentDecision(
                agent_name=self.name,
                bias="NEUTRAL",
                confidence=0.55,
                suggested_strategy="WAIT",
                reasoning="Insufficient forecast path to detect overextension.",
            )

        mean_price = float(np.mean(path))
        last_price = float(path[-1])
        z = (last_price - mean_price) / max(mean_price, 1e-6)

        if z > 0.03:
            confidence = 0.75 if regime == "RANGE_BOUND" else 0.7
            return AgentDecision(
                agent_name=self.name,
                bias="BEARISH",
                confidence=confidence,
                suggested_strategy="BEAR_CALL_SPREAD",
                reasoning="Projected path is overextended above its mean and may revert lower.",
            )

        if z < -0.03:
            confidence = 0.75 if regime == "RANGE_BOUND" else 0.7
            return AgentDecision(
                agent_name=self.name,
                bias="BULLISH",
                confidence=confidence,
                suggested_strategy="BULL_PUT_SPREAD",
                reasoning="Projected path is overextended below its mean and may revert upward.",
            )

        return AgentDecision(
            agent_name=self.name,
            bias="NEUTRAL",
            confidence=0.6,
            suggested_strategy="IRON_BUTTERFLY",
            reasoning="No significant overextension detected; neutral structures are favored.",
        )
