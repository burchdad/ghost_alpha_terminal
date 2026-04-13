from __future__ import annotations

from statistics import mean

from app.models.schemas import AgentDecision, ForecastResponse, OptionsChainResponse


class LiquidityFlowAgent:
    name = "liquidity_flow_agent"

    def run(
        self,
        symbol: str,
        forecast: ForecastResponse,
        options_data: OptionsChainResponse,
        regime: str | None = None,
    ) -> AgentDecision:
        sample = options_data.contracts[:20]
        if not sample:
            return AgentDecision(
                agent_name=self.name,
                bias="NEUTRAL",
                confidence=0.54,
                suggested_strategy="WAIT",
                reasoning="No options flow sample available.",
            )

        call_flow = sum(max(c.volume, 0) for c in sample if c.option_type == "CALL")
        put_flow = sum(max(c.volume, 0) for c in sample if c.option_type == "PUT")
        total_flow = max(call_flow + put_flow, 1)
        call_share = call_flow / total_flow

        oi_values = [max(c.open_interest, 0) for c in sample]
        avg_oi = mean(oi_values) if oi_values else 0

        if call_share >= 0.62 and avg_oi >= 150 and forecast.direction != "DOWN":
            return AgentDecision(
                agent_name=self.name,
                bias="BULLISH",
                confidence=0.72,
                suggested_strategy="FLOW_FOLLOW_CALL_VERTICAL",
                reasoning="Call-dominant flow with healthy open interest supports bullish continuation.",
            )

        if call_share <= 0.38 and avg_oi >= 150 and forecast.direction != "UP":
            return AgentDecision(
                agent_name=self.name,
                bias="BEARISH",
                confidence=0.72,
                suggested_strategy="FLOW_FOLLOW_PUT_VERTICAL",
                reasoning="Put-dominant flow with healthy open interest supports bearish continuation.",
            )

        return AgentDecision(
            agent_name=self.name,
            bias="NEUTRAL",
            confidence=0.6,
            suggested_strategy="WAIT",
            reasoning="Flow is mixed or too shallow for directional conviction.",
        )
