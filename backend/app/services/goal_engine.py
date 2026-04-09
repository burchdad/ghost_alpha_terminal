from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock


@dataclass
class GoalState:
    start_capital: float
    target_capital: float
    timeframe_days: int
    started_at: datetime


class GoalEngine:
    def __init__(self) -> None:
        self._lock = Lock()
        self._state: GoalState | None = None

    def configure(self, *, start_capital: float, target_capital: float, timeframe_days: int) -> dict:
        with self._lock:
            self._state = GoalState(
                start_capital=max(1.0, float(start_capital)),
                target_capital=max(1.0, float(target_capital)),
                timeframe_days=max(1, int(timeframe_days)),
                started_at=datetime.now(tz=timezone.utc),
            )
            return self._status_unlocked(current_capital=self._state.start_capital)

    def clear(self) -> None:
        with self._lock:
            self._state = None

    def current_pressure(self, *, current_capital: float) -> float:
        with self._lock:
            status = self._status_unlocked(current_capital=current_capital)
            return float(status["goal_pressure_multiplier"])

    def status(self, *, current_capital: float) -> dict:
        with self._lock:
            return self._status_unlocked(current_capital=current_capital)

    def _status_unlocked(self, *, current_capital: float) -> dict:
        if self._state is None:
            return {
                "enabled": False,
                "start_capital": None,
                "target_capital": None,
                "timeframe_days": None,
                "elapsed_days": 0.0,
                "remaining_days": None,
                "required_total_return": 0.0,
                "required_daily_return": 0.0,
                "required_daily_return_remaining": 0.0,
                "trajectory_expected_capital": None,
                "trajectory_gap_pct": 0.0,
                "goal_pressure_multiplier": 1.0,
                "target_unrealistic": False,
                "message": "No active goal. Pressure multiplier defaults to 1.0.",
            }

        now = datetime.now(tz=timezone.utc)
        elapsed_days = max((now - self._state.started_at).total_seconds() / 86400.0, 0.0)
        remaining_days = max(self._state.timeframe_days - elapsed_days, 0.0)

        start = self._state.start_capital
        target = self._state.target_capital
        current = max(1.0, float(current_capital))

        required_total_return = (target / start) - 1.0
        required_daily_return = (target / start) ** (1.0 / max(self._state.timeframe_days, 1)) - 1.0

        if remaining_days <= 0:
            required_daily_remaining = 0.0 if current >= target else 0.20
        else:
            required_daily_remaining = (target / current) ** (1.0 / remaining_days) - 1.0

        elapsed_steps = min(elapsed_days, float(self._state.timeframe_days))
        trajectory_expected = start * ((1.0 + required_daily_return) ** elapsed_steps)
        trajectory_gap_pct = (
            (trajectory_expected - current) / trajectory_expected if trajectory_expected > 0 else 0.0
        )

        baseline_daily_return = 0.002
        pressure_from_requirement = max(0.5, min(required_daily_remaining / baseline_daily_return, 2.5))
        trajectory_multiplier = max(0.7, min(1.0 + trajectory_gap_pct * 1.3, 1.6))
        pressure = max(0.5, min(pressure_from_requirement * trajectory_multiplier, 2.5))

        target_unrealistic = required_daily_remaining > 0.035
        message = "Goal pressure active."
        if target_unrealistic:
            message = "Target appears aggressive for remaining time; system will optimize probability, not guarantee outcomes."

        return {
            "enabled": True,
            "start_capital": round(start, 2),
            "target_capital": round(target, 2),
            "timeframe_days": self._state.timeframe_days,
            "elapsed_days": round(elapsed_days, 3),
            "remaining_days": round(remaining_days, 3),
            "required_total_return": round(required_total_return, 6),
            "required_daily_return": round(required_daily_return, 6),
            "required_daily_return_remaining": round(required_daily_remaining, 6),
            "trajectory_expected_capital": round(trajectory_expected, 2),
            "trajectory_gap_pct": round(trajectory_gap_pct, 6),
            "goal_pressure_multiplier": round(pressure, 4),
            "target_unrealistic": target_unrealistic,
            "message": message,
        }


goal_engine = GoalEngine()
