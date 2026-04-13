from __future__ import annotations

import math

from sqlalchemy import select

from app.db.models import AgentPrediction, TradeOutcome
from app.db.session import get_session
from app.models.schemas import AgentPerformance


class AgentScorer:
    def __init__(self) -> None:
        self._cache: dict[str, AgentPerformance | None] = {}

    def _cache_key(self, agent_name: str, symbol: str | None) -> str:
        normalized = symbol.upper() if symbol else "ALL"
        return f"{normalized}::{agent_name}"

    def _from_history(self, *, agent_name: str, symbol: str | None) -> AgentPerformance | None:
        wins: list[int] = []
        returns: list[float] = []
        predicted_confidences: list[float] = []

        with get_session() as db:
            stmt = select(AgentPrediction).where(AgentPrediction.agent_name == agent_name)
            if symbol:
                stmt = stmt.where(AgentPrediction.symbol == symbol.upper())
            predictions = db.execute(stmt.order_by(AgentPrediction.timestamp.desc()).limit(300)).scalars().all()

            for pred in predictions:
                outcome = db.execute(
                    select(TradeOutcome)
                    .where(
                        TradeOutcome.symbol == pred.symbol,
                        TradeOutcome.strategy == pred.strategy,
                        TradeOutcome.timestamp >= pred.timestamp,
                    )
                    .order_by(TradeOutcome.timestamp.asc())
                    .limit(1)
                ).scalars().first()

                if outcome is None:
                    continue

                realized = 1 if outcome.outcome == "WIN" else 0
                wins.append(realized)
                if outcome.entry_price != 0:
                    returns.append(outcome.pnl / abs(outcome.entry_price))
                predicted_confidences.append(pred.confidence)

        if not wins:
            return None

        accuracy = round(sum(wins) / len(wins), 3)
        win_rate = accuracy
        avg_return = round(sum(returns) / len(returns), 4) if returns else 0.0
        avg_predicted_confidence = sum(predicted_confidences) / len(predicted_confidences) if predicted_confidences else 0.6
        calibration = round(max(0.25, min(2.0, accuracy / max(avg_predicted_confidence, 1e-6))), 3)

        return_score = max(0.0, min(1.0, 0.5 + math.tanh(avg_return * 10) * 0.5))
        composite = round(accuracy * 0.35 + win_rate * 0.35 + calibration * 0.2 + return_score * 0.1, 3)

        return AgentPerformance(
            accuracy=accuracy,
            win_rate=win_rate,
            avg_return=avg_return,
            confidence_calibration=calibration,
            composite_score=composite,
        )

    def get_metrics(self, agent_name: str, symbol: str | None = None) -> AgentPerformance | None:
        key = self._cache_key(agent_name, symbol)
        if key not in self._cache:
            self._cache[key] = self._from_history(agent_name=agent_name, symbol=symbol)
        return self._cache[key]

    def invalidate(self, symbol: str | None = None) -> None:
        if symbol is None:
            self._cache.clear()
            return
        prefix = f"{symbol.upper()}::"
        removable = [key for key in self._cache if key.startswith(prefix)]
        for key in removable:
            self._cache.pop(key, None)


agent_scorer = AgentScorer()
