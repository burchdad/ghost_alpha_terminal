from __future__ import annotations

from statistics import mean

from app.models.schemas import AgentDecision, ForecastResponse, OptionsChainResponse


class OptionsAgent:
    name = "options_agent"

    def run(
        self,
        symbol: str,
        forecast: ForecastResponse,
        options_data: OptionsChainResponse,
        regime: str | None = None,
    ) -> AgentDecision:
        avg_iv = options_data.avg_iv
        deltas = [abs(c.delta) for c in options_data.contracts[:10]]
        avg_abs_delta = mean(deltas) if deltas else 0.5

        if avg_iv > 60:
            return AgentDecision(
                agent_name=self.name,
                bias="NEUTRAL",
                confidence=0.78 if regime == "HIGH_VOLATILITY" else 0.73,
                suggested_strategy="SELL_PREMIUM_SPREAD",
                reasoning="Elevated implied volatility favors defined-risk premium selling.",
            )

        if avg_iv < 30 and forecast.direction == "UP":
            return AgentDecision(
                agent_name=self.name,
                bias="BULLISH",
                confidence=0.76,
                suggested_strategy="LONG_CALL_VERTICAL",
                reasoning="Cheap implied volatility with bullish backdrop supports long call structures.",
            )

        if avg_abs_delta > 0.62 and forecast.direction == "DOWN":
            return AgentDecision(
                agent_name=self.name,
                bias="BEARISH",
                confidence=0.68,
                suggested_strategy="PUT_DEBIT_SPREAD",
                reasoning="Option sensitivity and bearish setup favor downside debit spreads.",
            )

        return AgentDecision(
            agent_name=self.name,
            bias="NEUTRAL",
            confidence=0.61,
            suggested_strategy="RISK_DEFINED_CONDOR",
            reasoning="Options surface is balanced; use neutral risk-defined structures.",
        )
