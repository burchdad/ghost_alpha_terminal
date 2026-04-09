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
                "success_probability": 0.5,
                "stress_level": "LOW",
                "target_unrealistic": False,
                "suggested_target_capital": None,
                "suggested_timeframe_days": None,
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
        if required_daily_remaining <= 0:
            success_probability = 0.99
        else:
            annualized_vol = 0.28
            horizon_scale = max(0.45, min((remaining_days / 30.0) ** 0.5, 1.75))
            difficulty = required_daily_remaining / max(0.0015 * horizon_scale, 1e-6)
            trajectory_penalty = max(0.0, trajectory_gap_pct) * 1.5
            pressure_penalty = max(0.0, pressure - 1.0) * 0.25
            vol_penalty = max(0.0, annualized_vol - 0.22) * 0.35
            raw_prob = 1.15 - (difficulty * 0.42) - trajectory_penalty - pressure_penalty - vol_penalty
            success_probability = max(0.01, min(raw_prob, 0.99))

        if pressure >= 1.8 or success_probability < 0.20:
            stress_level = "EXTREME"
        elif pressure >= 1.4 or success_probability < 0.40:
            stress_level = "HIGH"
        elif pressure >= 1.0 or success_probability < 0.65:
            stress_level = "MEDIUM"
        else:
            stress_level = "LOW"

        suggested_target_capital = None
        suggested_timeframe_days = None
        if target_unrealistic or success_probability < 0.25:
            conservative_daily = 0.004
            suggested_target_capital = current * ((1.0 + conservative_daily) ** max(remaining_days, 1.0))
            needed_days = 30.0
            if target > current:
                needed_days = max(30.0, (target / current))
                needed_days *= 42.0
            suggested_timeframe_days = int(min(max(round(needed_days), 30), 1460))

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
            "success_probability": round(success_probability, 4),
            "stress_level": stress_level,
            "target_unrealistic": target_unrealistic,
            "suggested_target_capital": round(suggested_target_capital, 2) if suggested_target_capital is not None else None,
            "suggested_timeframe_days": suggested_timeframe_days,
            "message": message,
        }


goal_engine = GoalEngine()
