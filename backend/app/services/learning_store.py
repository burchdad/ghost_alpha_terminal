from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from sqlalchemy import case, func, select

from app.db.models import AgentPrediction, ForecastHistory, SignalHistory, TradeOutcome
from app.db.session import get_session
from app.models.schemas import AgentDecision, ForecastResponse, SignalResponse, SwarmResponse, TradeOutcomeResponse


class LearningStore:
    def save_swarm_snapshot(
        self,
        *,
        symbol: str,
        forecast: ForecastResponse,
        signal: SignalResponse,
        swarm: SwarmResponse,
        agent_outputs: Iterable[AgentDecision],
    ) -> None:
        with get_session() as db:
            db.add(
                ForecastHistory(
                    symbol=symbol.upper(),
                    timestamp=forecast.generated_at,
                    direction=forecast.direction,
                    confidence=forecast.confidence,
                    volatility=forecast.volatility,
                )
            )

            db.add(
                SignalHistory(
                    symbol=symbol.upper(),
                    signal=signal.signal,
                    confidence=signal.confidence,
                    reasoning=signal.reasoning,
                    timestamp=signal.generated_at,
                )
            )

            db.add(
                SignalHistory(
                    symbol=symbol.upper(),
                    signal=swarm.consensus.top_strategy,
                    confidence=swarm.consensus.confidence,
                    reasoning=f"swarm_consensus:{swarm.consensus.final_bias}",
                    timestamp=swarm.generated_at,
                )
            )

            for agent in agent_outputs:
                db.add(
                    AgentPrediction(
                        symbol=symbol.upper(),
                        agent_name=agent.agent_name,
                        bias=agent.bias,
                        confidence=agent.confidence,
                        strategy=agent.suggested_strategy,
                        timestamp=swarm.generated_at,
                    )
                )

    def record_trade_outcome(
        self,
        *,
        symbol: str,
        strategy: str,
        regime: str,
        entry_price: float,
        exit_price: float,
    ) -> TradeOutcomeResponse:
        pnl = round(exit_price - entry_price, 4)
        outcome = "WIN" if pnl >= 0 else "LOSS"
        now = datetime.now(tz=timezone.utc)

        with get_session() as db:
            db.add(
                TradeOutcome(
                    symbol=symbol.upper(),
                    strategy=strategy,
                    regime=regime,
                    entry_price=entry_price,
                    exit_price=exit_price,
                    pnl=pnl,
                    outcome=outcome,
                    timestamp=now,
                )
            )

        return TradeOutcomeResponse(
            symbol=symbol.upper(),
            strategy=strategy,
            regime=regime,
            entry_price=entry_price,
            exit_price=exit_price,
            pnl=pnl,
            outcome=outcome,
            timestamp=now,
        )

    def get_strategy_success_rates(self, *, symbol: str) -> list[dict]:
        with get_session() as db:
            rows = db.execute(
                select(
                    TradeOutcome.strategy,
                    func.count(TradeOutcome.id).label("trades"),
                    func.avg(case((TradeOutcome.outcome == "WIN", 1), else_=0)).label("win_rate"),
                    func.avg(TradeOutcome.pnl).label("avg_pnl"),
                )
                .where(TradeOutcome.symbol == symbol.upper())
                .group_by(TradeOutcome.strategy)
            ).all()

        result = []
        for row in rows:
            result.append(
                {
                    "strategy": row.strategy,
                    "trades": int(row.trades),
                    "win_rate": round(float(row.win_rate or 0.0), 3),
                    "avg_pnl": round(float(row.avg_pnl or 0.0), 4),
                }
            )
        return sorted(result, key=lambda x: (x["win_rate"], x["avg_pnl"]), reverse=True)

    def get_regime_performance(self, *, symbol: str) -> dict[str, dict[str, float | int]]:
        with get_session() as db:
            rows = db.execute(
                select(
                    TradeOutcome.regime,
                    func.count(TradeOutcome.id).label("total_trades"),
                    func.avg(case((TradeOutcome.outcome == "WIN", 1), else_=0)).label("win_rate"),
                    func.avg(TradeOutcome.pnl).label("avg_pnl"),
                )
                .where(TradeOutcome.symbol == symbol.upper())
                .group_by(TradeOutcome.regime)
            ).all()

        by_regime: dict[str, dict[str, float | int]] = {
            "TRENDING": {"win_rate": 0.0, "avg_pnl": 0.0, "total_trades": 0},
            "RANGE_BOUND": {"win_rate": 0.0, "avg_pnl": 0.0, "total_trades": 0},
            "HIGH_VOLATILITY": {"win_rate": 0.0, "avg_pnl": 0.0, "total_trades": 0},
        }

        for row in rows:
            by_regime[row.regime] = {
                "win_rate": round(float(row.win_rate or 0.0), 3),
                "avg_pnl": round(float(row.avg_pnl or 0.0), 4),
                "total_trades": int(row.total_trades),
            }

        return by_regime


learning_store = LearningStore()
