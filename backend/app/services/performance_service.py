from __future__ import annotations

from datetime import datetime, timezone

from app.models.schemas import AgentPerformanceRow, PerformanceResponse, StrategyPerformanceRow
from app.services.agent_registry import get_registered_agents
from app.services.agent_scorer import agent_scorer
from app.services.learning_store import learning_store


class PerformanceService:
    def get_performance(self, symbol: str) -> PerformanceResponse:
        symbol = symbol.upper()
        agent_rows: list[AgentPerformanceRow] = []

        for agent in get_registered_agents():
            metrics = agent_scorer.get_metrics(agent.name, symbol=symbol)
            if metrics is None:
                continue
            agent_rows.append(
                AgentPerformanceRow(
                    agent_name=agent.name,
                    accuracy=metrics.accuracy,
                    win_rate=metrics.win_rate,
                    avg_return=metrics.avg_return,
                    confidence_calibration=metrics.confidence_calibration,
                    composite_score=metrics.composite_score,
                )
            )

        agent_rows.sort(key=lambda row: row.composite_score, reverse=True)
    best_agent = agent_rows[0].agent_name if agent_rows else "insufficient_history"

        strategy_rows = [StrategyPerformanceRow(**item) for item in learning_store.get_strategy_success_rates(symbol=symbol)]
        by_regime = learning_store.get_regime_performance(symbol=symbol)

        return PerformanceResponse(
            symbol=symbol,
            best_agent=best_agent,
            agent_leaderboard=agent_rows,
            top_strategies=strategy_rows,
            by_regime=by_regime,
            generated_at=datetime.now(tz=timezone.utc),
        )


performance_service = PerformanceService()
