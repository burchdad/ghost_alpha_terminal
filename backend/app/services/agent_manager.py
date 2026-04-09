from __future__ import annotations

from app.models.schemas import AgentDecision, ForecastResponse, OptionsChainResponse
from app.services.agent_registry import get_registered_agents


class AgentManager:
    def run_agents(
        self,
        symbol: str,
        forecast: ForecastResponse,
        options_data: OptionsChainResponse,
        regime: str | None = None,
    ) -> list[AgentDecision]:
        outputs: list[AgentDecision] = []
        for agent in get_registered_agents():
            outputs.append(agent.run(symbol=symbol, forecast=forecast, options_data=options_data, regime=regime))
        return outputs


agent_manager = AgentManager()
