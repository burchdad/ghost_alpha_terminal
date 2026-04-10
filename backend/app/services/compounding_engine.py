from __future__ import annotations


class CompoundingEngine:
    """Adaptive reinvestment policy for intentional account growth."""

    def plan(
        self,
        *,
        goal_pressure: float,
        drawdown_pct: float,
        recent_win_rate: float,
    ) -> dict:
        pressure = max(0.5, min(goal_pressure, 2.5))
        drawdown = max(0.0, min(drawdown_pct, 1.0))
        win_rate = max(0.0, min(recent_win_rate, 1.0))

        if drawdown >= 0.08:
            style = "defensive"
            reinvestment_multiplier = 0.80
            risk_budget_multiplier = 0.75
        elif pressure >= 1.8 and win_rate >= 0.52 and drawdown <= 0.03:
            style = "aggressive"
            reinvestment_multiplier = 1.20
            risk_budget_multiplier = 1.15
        elif pressure >= 1.35 and win_rate >= 0.48 and drawdown <= 0.05:
            style = "growth"
            reinvestment_multiplier = 1.10
            risk_budget_multiplier = 1.08
        else:
            style = "balanced"
            reinvestment_multiplier = 1.0
            risk_budget_multiplier = 1.0

        return {
            "style": style,
            "reinvestment_multiplier": round(reinvestment_multiplier, 4),
            "risk_budget_multiplier": round(risk_budget_multiplier, 4),
        }


compounding_engine = CompoundingEngine()
