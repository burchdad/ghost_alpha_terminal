from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select

from app.db.models import LaunchMetricDaily
from app.db.session import get_session


class LightweightMetrics:
    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _today(self) -> date:
        return self._now().date()

    def _upsert_metric(
        self,
        *,
        day: date,
        metric_type: str,
        increment: int,
        strategy: str | None = None,
    ) -> None:
        with get_session() as session:
            stmt = select(LaunchMetricDaily).where(
                LaunchMetricDaily.day == day,
                LaunchMetricDaily.metric_type == metric_type,
                LaunchMetricDaily.strategy == strategy,
            )
            row = session.execute(stmt).scalar_one_or_none()
            if row is None:
                row = LaunchMetricDaily(
                    day=day,
                    metric_type=metric_type,
                    strategy=strategy,
                    metric_count=0,
                    updated_at=self._now(),
                )
                session.add(row)
            row.metric_count += increment
            row.updated_at = self._now()

    def record_scan(self, strategy_types: list[str]) -> None:
        day = self._today()
        self._upsert_metric(day=day, metric_type="scans_run", increment=1)

        counts = Counter(strategy_types)
        for strategy, count in counts.items():
            self._upsert_metric(
                day=day,
                metric_type="strategies_selected",
                strategy=strategy,
                increment=int(count),
            )

    def record_trade(self, strategy: str) -> None:
        day = self._today()
        self._upsert_metric(day=day, metric_type="trades_triggered", increment=1)
        self._upsert_metric(
            day=day,
            metric_type="strategies_selected",
            strategy=strategy,
            increment=1,
        )

    def summary(self, days: int = 7) -> dict:
        days = max(1, min(days, 30))
        today = self._today()
        start_day = today - timedelta(days=days - 1)

        with get_session() as session:
            rows = session.execute(
                select(LaunchMetricDaily).where(LaunchMetricDaily.day >= start_day)
            ).scalars().all()

        scans_run = sum(r.metric_count for r in rows if r.metric_type == "scans_run")
        trades_triggered = sum(r.metric_count for r in rows if r.metric_type == "trades_triggered")

        strategy_counts: dict[str, int] = {}
        for row in rows:
            if row.metric_type != "strategies_selected" or not row.strategy:
                continue
            strategy_counts[row.strategy] = strategy_counts.get(row.strategy, 0) + row.metric_count

        top_strategies = [
            {"strategy": s, "count": c}
            for s, c in sorted(strategy_counts.items(), key=lambda item: item[1], reverse=True)
        ]

        return {
            "window_days": days,
            "start_day": start_day.isoformat(),
            "end_day": today.isoformat(),
            "scans_run": scans_run,
            "trades_triggered": trades_triggered,
            "strategies_selected": strategy_counts,
            "top_strategies": top_strategies[:5],
        }


lightweight_metrics = LightweightMetrics()
