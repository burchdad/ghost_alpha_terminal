from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from statistics import pstdev

from app.core.config import settings
from app.services.compounding_engine import compounding_engine
from app.services.control_engine import control_engine
from app.services.execution_quality_engine import execution_quality_engine
from app.services.goal_engine import goal_engine
from app.services.live_experiment_promotion_service import live_experiment_promotion_service
from app.services.live_portfolio_service import live_portfolio_service
from app.services.master_orchestrator import master_orchestrator
from app.services.meta_risk_governor import meta_risk_governor
from app.services.mission_policy_engine import mission_policy_engine
from app.services.parity_watchdog_service import parity_watchdog_service
from app.services.portfolio_manager import portfolio_manager
from app.services.strategy_evolution_service import strategy_evolution_service
from app.services.system_mode_service import system_mode_service
from app.services.execution_journal import execution_journal


class MissionIntelligenceService:
    @staticmethod
    def _operator_alerts(*, system_mode: dict) -> list[dict]:
        predictive = system_mode.get("predictive_prevention", {}) or {}
        warning_score = float(predictive.get("warning_score", 0.0) or 0.0)
        early_warning = bool(predictive.get("early_warning", False))
        preventive_shift_applied = bool(predictive.get("preventive_shift_applied", False))
        signals = [str(signal) for signal in (predictive.get("signals", []) or []) if str(signal)]
        target_mode = str(predictive.get("preventive_mode") or "DEFENSIVE")

        if warning_score < 0.22 and not early_warning and not preventive_shift_applied:
            return []

        if preventive_shift_applied:
            phase = "PREVENTIVE_SHIFT"
            severity = "WARNING"
            title = "Predictive Defensive Shift Active"
            message = (
                f"Predictive warning score {warning_score:.2f} shifted controls toward "
                f"{target_mode.replace('_', ' ')} before hard failure thresholds."
            )
        elif early_warning:
            phase = "EARLY_WARNING"
            severity = "WARNING"
            title = "Predictive Failure Warning"
            message = (
                f"Predictive warning score {warning_score:.2f} indicates a likely "
                f"{target_mode.replace('_', ' ')} downgrade if deterioration continues."
            )
        else:
            phase = "WATCH"
            severity = "INFO"
            message = (
                f"Predictive warning score {warning_score:.2f} is rising; operators should watch for a "
                f"{target_mode.replace('_', ' ')} downgrade."
            )
            title = "Predictive Degradation Watch"

        if signals:
            message = f"{message} Signals: {', '.join(signals[:3])}."

        return [
            {
                "code": "system_mode_predictive_prevention",
                "phase": phase,
                "severity": severity,
                "title": title,
                "message": message,
                "score": round(warning_score, 4),
                "target_mode": target_mode,
                "signals": signals,
            }
        ]

    @staticmethod
    def _window_confidence(*, days: int, now: datetime) -> dict:
        start = now - timedelta(days=days)
        rows = [
            row
            for row in execution_journal.recent(limit=2000)
            if isinstance(row.timestamp, datetime)
            and row.timestamp >= start
            and str(row.outcome_label or "").upper() in {"WIN", "LOSS"}
            and row.pnl is not None
        ]

        if not rows:
            return {
                "days": days,
                "score": 0.35,
                "win_rate": 0.5,
                "net_pnl": 0.0,
                "sample_size": 0,
            }

        wins = sum(1 for row in rows if str(row.outcome_label).upper() == "WIN")
        win_rate = wins / max(len(rows), 1)
        net_pnl = sum(float(row.pnl or 0.0) for row in rows)
        sufficiency = max(0.0, min(len(rows) / 60.0, 1.0))
        pnl_term = max(0.0, min(0.5 + (net_pnl / max(len(rows), 1)) / 200.0, 1.0))
        score = max(0.0, min(win_rate * 0.6 + sufficiency * 0.25 + pnl_term * 0.15, 1.0))
        return {
            "days": days,
            "score": round(score, 4),
            "win_rate": round(win_rate, 4),
            "net_pnl": round(net_pnl, 2),
            "sample_size": len(rows),
        }

    @staticmethod
    def _system_confidence(*, quality: dict, drawdown_pct: float) -> dict:
        sample_size = int(quality.get("sample_size", 0) or 0)
        strategy_quality = quality.get("strategy_quality", {}) or {}
        win_rates = [
            float((stats or {}).get("win_rate", 0.5) or 0.5)
            for stats in strategy_quality.values()
            if int((stats or {}).get("settled", 0) or 0) > 0
        ]

        data_sufficiency = max(0.0, min(sample_size / 120.0, 1.0))
        strategy_diversity = max(0.0, min(len(strategy_quality) / 6.0, 1.0))
        win_rate_stability = 1.0
        if len(win_rates) >= 2:
            win_rate_stability = max(0.0, 1.0 - min(pstdev(win_rates) / 0.20, 1.0))
        drawdown_pressure = max(0.0, 1.0 - min(max(drawdown_pct, 0.0) / 0.12, 1.0))

        score = (
            data_sufficiency * 0.30
            + strategy_diversity * 0.20
            + win_rate_stability * 0.25
            + drawdown_pressure * 0.25
        )
        label = "HIGH" if score >= 0.72 else "MEDIUM" if score >= 0.52 else "LOW"
        return {
            "score": round(score, 4),
            "label": label,
            "factors": {
                "data_sufficiency": round(data_sufficiency, 4),
                "strategy_diversity": round(strategy_diversity, 4),
                "win_rate_stability": round(win_rate_stability, 4),
                "drawdown_pressure": round(drawdown_pressure, 4),
            },
        }

    def snapshot(self) -> dict:
        portfolio = live_portfolio_service.snapshot() or portfolio_manager.snapshot()
        control = control_engine.status()
        goal = goal_engine.status(current_capital=float(portfolio.get("account_balance", 0.0) or 0.0))
        quality = execution_quality_engine.summary(limit=500)
        now = datetime.now(tz=timezone.utc)

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

        strategy_quality = quality.get("strategy_quality", {})
        strategy_win_rates = [float((stats or {}).get("win_rate", 0.5) or 0.5) for stats in strategy_quality.values()]
        avg_strategy_win_rate = sum(strategy_win_rates) / max(len(strategy_win_rates), 1)
        compounding = compounding_engine.plan(
            goal_pressure=goal_pressure,
            drawdown_pct=float(control.get("rolling_drawdown_pct", 0.0) or 0.0),
            recent_win_rate=avg_strategy_win_rate,
        )
        evolution = strategy_evolution_service.plan(strategy_quality=strategy_quality)
        confidence_7d = self._window_confidence(days=7, now=now)
        confidence_30d = self._window_confidence(days=30, now=now)
        confidence_90d = self._window_confidence(days=90, now=now)
        time_weighted_confidence = {
            "short_term_7d": confidence_7d,
            "mid_term_30d": confidence_30d,
            "long_term_90d": confidence_90d,
            "blended_score": round(
                float(confidence_7d.get("score", 0.0)) * 0.35
                + float(confidence_30d.get("score", 0.0)) * 0.40
                + float(confidence_90d.get("score", 0.0)) * 0.25,
                4,
            ),
        }
        system_confidence = self._system_confidence(
            quality=quality,
            drawdown_pct=float(control.get("rolling_drawdown_pct", 0.0) or 0.0),
        )
        meta_risk = meta_risk_governor.evaluate(
            drawdown_pct=float(control.get("rolling_drawdown_pct", 0.0) or 0.0)
        )
        live_mode = live_experiment_promotion_service.status()
        system_mode = system_mode_service.evaluate(
            goal_pressure=goal_pressure,
            drawdown_pct=float(control.get("rolling_drawdown_pct", 0.0) or 0.0),
            quality=quality,
            meta_risk=meta_risk,
            live_mode=live_mode,
        )
        system_controls = system_mode.get("controls", {}) or {}
        if not bool(system_controls.get("allow_evolution", True)):
            evolution = {"mutations": [], "clones": [], "reinforcement_weights": {}, "suggested_experiments": 0}
        if not bool(system_controls.get("allow_compounding", True)):
            compounding = {
                **compounding,
                "reinvestment_multiplier": 1.0,
                "risk_budget_multiplier": 1.0,
            }
        mission = mission_policy_engine.mission_snapshot(
            goal_status=goal,
            drawdown_pct=float(control.get("rolling_drawdown_pct", 0.0) or 0.0),
            sprint_active=sprint_active,
            dominant_regime=regime,
            regime_quality=quality.get("regime_quality", {}),
            bucket_quality=quality.get("bucket_quality", {}),
            system_mode=system_mode,
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
            "compounding": compounding,
            "strategy_evolution": evolution,
            "time_weighted_confidence": time_weighted_confidence,
            "system_confidence": system_confidence,
            "system_mode": system_mode,
            "operator_alerts": self._operator_alerts(system_mode=system_mode),
            "meta_risk_governor": meta_risk,
            "live_experiment_mode": live_mode,
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
                "bucket_quality": quality.get("bucket_quality", {}),
                "disabled_strategies": quality.get("disabled_strategies", []),
                "probation_strategies": quality.get("probation_strategies", []),
                "forced_retest_strategies": quality.get("forced_retest_strategies", []),
                "strategy_kill_switches": quality.get("strategy_kill_switches", []),
                "strategy_states": quality.get("strategy_states", []),
                "strategy_lifecycle_transitions": quality.get("strategy_lifecycle_transitions", []),
                "strategy_lifecycle_transition_summary": quality.get("strategy_lifecycle_transition_summary", {}),
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
