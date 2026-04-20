from __future__ import annotations

from app.models.schemas import AgentDecision, ForecastResponse, OptionsChainResponse


class TermStructureAgent:
    name = "term_structure_agent"

    def run(
        self,
        symbol: str,
        forecast: ForecastResponse,
        options_data: OptionsChainResponse,
        regime: str | None = None,
    ) -> AgentDecision:
        contracts = options_data.contracts[:16]
        if len(contracts) < 4:
            return AgentDecision(
                agent_name=self.name,
                bias="NEUTRAL",
                confidence=0.55,
                suggested_strategy="WAIT",
                reasoning="Insufficient options surface depth for term-structure read.",
            )

        near = [c for c in contracts[:8] if c.iv > 0]
        far = [c for c in contracts[8:16] if c.iv > 0]
        near_iv = sum(c.iv for c in near) / len(near) if near else options_data.avg_iv
        far_iv = sum(c.iv for c in far) / len(far) if far else options_data.avg_iv

        # Positive slope: longer-dated vol richer than near-term; favor calendars.
        if far_iv - near_iv > 4.0:
            return AgentDecision(
                agent_name=self.name,
                bias="NEUTRAL",
                confidence=0.73,
                suggested_strategy="LONG_CALENDAR_SPREAD",
                reasoning="Upward term structure supports calendar-style vega positioning.",
            )

        # Inversion: near-term fear elevated; favor premium harvesting if directional edge is weak.
        if near_iv - far_iv > 6.0 and forecast.confidence < 0.72:
            return AgentDecision(
                agent_name=self.name,
                bias="NEUTRAL",
                confidence=0.75,
                suggested_strategy="SHORT_PREMIUM_FRONT_WEEK",
                reasoning="Near-term IV inversion with moderate directional edge favors front premium capture.",
            )

        bias = "BULLISH" if forecast.direction == "UP" else "BEARISH" if forecast.direction == "DOWN" else "NEUTRAL"
        strat = "CALL_DIAGONAL" if bias == "BULLISH" else "PUT_DIAGONAL" if bias == "BEARISH" else "WAIT"
        return AgentDecision(
            agent_name=self.name,
            bias=bias,
            confidence=0.63,
            suggested_strategy=strat,
            reasoning="Balanced term structure; use directional diagonal aligned with forecast.",
        )
