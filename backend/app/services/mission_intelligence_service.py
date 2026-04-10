from __future__ import annotations

from collections import Counter

from app.core.config import settings
from app.services.control_engine import control_engine
from app.services.execution_quality_engine import execution_quality_engine
from app.services.goal_engine import goal_engine
from app.services.live_portfolio_service import live_portfolio_service
from app.services.master_orchestrator import master_orchestrator
from app.services.mission_policy_engine import mission_policy_engine
from app.services.parity_watchdog_service import parity_watchdog_service
from app.services.portfolio_manager import portfolio_manager


class MissionIntelligenceService:
    def snapshot(self) -> dict:
        portfolio = live_portfolio_service.snapshot() or portfolio_manager.snapshot()
        control = control_engine.status()
        goal = goal_engine.status(current_capital=float(portfolio.get("account_balance", 0.0) or 0.0))
        quality = execution_quality_engine.summary(limit=500)

        latest = master_orchestrator.latest()
        regime = "RANGE_BOUND"
        sprint_symbols: list[str] = []
        if latest is not None and getattr(latest, "candidates", None):
            regimes = Counter(getattr(c, "regime", "RANGE_BOUND") for c in latest.candidates)
            regime = regimes.most_common(1)[0][0] if regimes else "RANGE_BOUND"
            sprint_symbols = [c.symbol for c in latest.candidates if getattr(c, "symbol", "") and "high_risk_sprint" in str(getattr(c, "reasoning", "")).lower()]

        goal_pressure = float(goal.get("goal_pressure_multiplier", 1.0) or 1.0)
        sprint_active = bool(
            settings.high_risk_sprint_mode_enabled
            or (
                settings.high_risk_sprint_auto_enabled
                and goal_pressure >= settings.high_risk_sprint_auto_trigger_pressure
            )
        )

        mission = mission_policy_engine.mission_snapshot(
            goal_status=goal,
            drawdown_pct=float(control.get("rolling_drawdown_pct", 0.0) or 0.0),
            sprint_active=sprint_active,
            dominant_regime=regime,
            regime_quality=quality.get("regime_quality", {}),
        )

        best_symbols = sorted(
            quality.get("symbol_quality", {}).items(),
            key=lambda kv: kv[1].get("quality_score", 0.0),
            reverse=True,
        )[:5]
        worst_symbols = sorted(
            quality.get("symbol_quality", {}).items(),
            key=lambda kv: kv[1].get("quality_score", 1.0),
        )[:5]

        return {
            "mission": mission,
            "sprint_governance": {
                "active": sprint_active,
                "manual_override": bool(settings.high_risk_sprint_mode_enabled),
                "auto_enabled": bool(settings.high_risk_sprint_auto_enabled),
                "trigger_pressure": float(settings.high_risk_sprint_auto_trigger_pressure),
                "current_pressure": round(goal_pressure, 4),
                "admitted_symbols": sprint_symbols,
                "extra_risk_budget_pct": 0.06 if sprint_active else 0.0,
                "deactivation_condition": "Goal pressure drops below trigger and manual override is disabled.",
            },
            "execution_quality": {
                "sample_size": quality.get("sample_size", 0),
                "top_symbols": [{"symbol": sym, **stats} for sym, stats in best_symbols],
                "bottom_symbols": [{"symbol": sym, **stats} for sym, stats in worst_symbols],
                "asset_class_quality": quality.get("asset_class_quality", {}),
                "regime_quality": quality.get("regime_quality", {}),
                "strategy_quality": quality.get("strategy_quality", {}),
                "confidence_band_quality": quality.get("confidence_band_quality", {}),
            },
            "parity_watchdog": parity_watchdog_service.status(),
        }

    def simulate_mission(self, *, target_capital: float, timeframe_days: int, start_capital: float | None = None) -> dict:
        portfolio = live_portfolio_service.snapshot() or portfolio_manager.snapshot()
        current = float(start_capital if start_capital is not None else portfolio.get("account_balance", 0.0) or 0.0)
        return mission_policy_engine.simulate_scenario(
            current_capital=current,
            target_capital=target_capital,
            timeframe_days=timeframe_days,
        )


mission_intelligence_service = MissionIntelligenceService()
