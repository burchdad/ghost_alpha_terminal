from __future__ import annotations

import threading
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone


TRACKED_TRANSITIONS = {
    ("enabled", "probation"),
    ("probation", "forced_retest"),
    ("forced_retest", "enabled"),
    ("forced_retest", "disabled"),
}


@dataclass
class StrategyLifecycleTransition:
    strategy: str
    from_state: str
    to_state: str
    win_rate: float
    window_trades: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))


class StrategyLifecycleTransitionStore:
    """Tracks strategy lifecycle transitions to detect stabilization vs. thrashing."""

    def __init__(self, maxlen: int = 2000) -> None:
        self._lock = threading.Lock()
        self._events: deque[StrategyLifecycleTransition] = deque(maxlen=maxlen)
        self._last_state_by_strategy: dict[str, str] = {}

    @staticmethod
    def _normalize(value: str) -> str:
        return str(value or "").strip().lower()

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime:
        if value is None:
            return datetime.now(tz=timezone.utc)
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def record_state(
        self,
        *,
        strategy: str,
        state: str,
        win_rate: float,
        window_trades: int,
        timestamp: datetime | None = None,
    ) -> None:
        name = str(strategy or "").strip().upper()
        if not name:
            return

        next_state = self._normalize(state)
        if not next_state:
            return

        when = self._as_utc(timestamp)

        with self._lock:
            prev_state = self._last_state_by_strategy.get(name)
            self._last_state_by_strategy[name] = next_state
            if not prev_state or prev_state == next_state:
                return
            if (prev_state, next_state) not in TRACKED_TRANSITIONS:
                return
            self._events.append(
                StrategyLifecycleTransition(
                    strategy=name,
                    from_state=prev_state,
                    to_state=next_state,
                    win_rate=round(float(win_rate), 4),
                    window_trades=int(window_trades),
                    timestamp=when,
                )
            )

    def recent(self, *, limit: int = 200, since_hours: int | None = None) -> list[dict]:
        with self._lock:
            events = list(self._events)

        if since_hours is not None and since_hours > 0:
            cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=since_hours)
            events = [event for event in events if event.timestamp >= cutoff]

        events = events[-max(1, limit) :]
        return [
            {
                "strategy": event.strategy,
                "from_state": event.from_state,
                "to_state": event.to_state,
                "win_rate": event.win_rate,
                "window_trades": event.window_trades,
                "timestamp": event.timestamp.isoformat(),
            }
            for event in events
        ]

    def summary(self, *, since_hours: int = 24) -> dict:
        rows = self.recent(limit=2000, since_hours=since_hours)
        transition_counter: Counter[str] = Counter(
            f"{row['from_state']}->{row['to_state']}" for row in rows
        )
        strategy_counter: Counter[str] = Counter(row["strategy"] for row in rows)
        thrashing_strategies = [
            {"strategy": strategy, "transitions": count}
            for strategy, count in strategy_counter.items()
            if count >= 3
        ]
        thrashing_strategies.sort(key=lambda item: item["transitions"], reverse=True)

        return {
            "since_hours": since_hours,
            "total_transitions": len(rows),
            "transition_counts": dict(sorted(transition_counter.items())),
            "thrashing_strategies": thrashing_strategies,
            "stability_state": "THRASHING" if thrashing_strategies else "STABILIZING",
        }


strategy_lifecycle_transition_store = StrategyLifecycleTransitionStore()
