from __future__ import annotations

from datetime import datetime, timezone
from statistics import pstdev
from typing import Literal


SystemMode = Literal["AGGRESSIVE_GROWTH", "BALANCED", "DEFENSIVE", "SURVIVAL"]


class SystemModeService:
    """Computes a system-wide identity that coordinates behavior across subsystems."""

    @staticmethod
    def _safe_iso_age_hours(value: str | None) -> float | None:
        if not value:
            return None
        try:
            ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            else:
                ts = ts.astimezone(timezone.utc)
            return max(0.0, (datetime.now(tz=timezone.utc) - ts).total_seconds() / 3600.0)
        except Exception:
            return None

    @staticmethod
    def _system_confidence_score(*, quality: dict, drawdown_pct: float) -> float:
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
        return max(
            0.0,
            min(
                data_sufficiency * 0.30
                + strategy_diversity * 0.20
                + win_rate_stability * 0.25
                + drawdown_pressure * 0.25,
                1.0,
            ),
        )

    @staticmethod
    def _experiment_instability(*, quality: dict, meta_risk: dict, live_mode: dict) -> dict:
        transition_summary = quality.get("strategy_lifecycle_transition_summary", {}) or {}
        transitions = int(transition_summary.get("total_transitions", 0) or 0)
        thrashing_count = len(transition_summary.get("thrashing_strategies", []) or [])
        strategy_quality = quality.get("strategy_quality", {}) or {}
        win_rates = [
            float((stats or {}).get("win_rate", 0.5) or 0.5)
            for stats in strategy_quality.values()
            if int((stats or {}).get("settled", 0) or 0) > 0
        ]
        dispersion = min(pstdev(win_rates) / 0.18, 1.0) if len(win_rates) >= 2 else 0.25
        age_hours = SystemModeService._safe_iso_age_hours(str(live_mode.get("promoted_at") or "") or None)
        recent_promotion = 0.0
        if age_hours is not None:
            recent_promotion = max(0.0, min((72.0 - age_hours) / 72.0, 1.0))
        meta_mode = str(meta_risk.get("mode", "normal") or "normal")
        meta_pressure = 1.0 if meta_mode == "critical" else 0.6 if meta_mode == "elevated" else 0.15

        score = max(
            0.0,
            min(
                min(transitions / 10.0, 1.0) * 0.30
                + min(thrashing_count / 3.0, 1.0) * 0.20
                + dispersion * 0.25
                + recent_promotion * 0.10
                + meta_pressure * 0.15,
                1.0,
            ),
        )
        return {
            "score": round(score, 4),
            "transitions_last_window": transitions,
            "thrashing_strategies": thrashing_count,
            "win_rate_dispersion": round(dispersion, 4),
            "recent_promotion_pressure": round(recent_promotion, 4),
        }

    def evaluate(
        self,
        *,
        goal_pressure: float,
        drawdown_pct: float,
        quality: dict,
        meta_risk: dict,
        live_mode: dict,
    ) -> dict:
        confidence_score = self._system_confidence_score(quality=quality, drawdown_pct=drawdown_pct)
        confidence_label = "HIGH" if confidence_score >= 0.72 else "MEDIUM" if confidence_score >= 0.52 else "LOW"
        experiment_instability = self._experiment_instability(quality=quality, meta_risk=meta_risk, live_mode=live_mode)
        instability_score = float(experiment_instability.get("score", 0.0) or 0.0)
        meta_mode = str(meta_risk.get("mode", "normal") or "normal")
        confidence_collapse = bool((meta_risk.get("confidence_collapse") or {}).get("collapse", False))
        correlation_spike = bool((meta_risk.get("correlation_spike") or {}).get("spike", False))

        if (
            meta_mode == "critical"
            or drawdown_pct >= 0.10
            or confidence_score < 0.45
            or instability_score >= 0.72
            or (confidence_collapse and correlation_spike)
        ):
            mode: SystemMode = "SURVIVAL"
            reason = "System capital protection mode due to stress, instability, or collapse signals."
        elif meta_mode == "elevated" or drawdown_pct >= 0.06 or confidence_score < 0.58 or instability_score >= 0.55:
            mode = "DEFENSIVE"
            reason = "System reducing aggression because edge quality or stability deteriorated."
        elif (
            meta_mode == "normal"
            and drawdown_pct <= 0.025
            and confidence_score >= 0.74
            and instability_score <= 0.35
            and goal_pressure >= 1.10
        ):
            mode = "AGGRESSIVE_GROWTH"
            reason = "System pressing edge while confidence is high and instability remains controlled."
        else:
            mode = "BALANCED"
            reason = "System operating in steady-state growth mode."

        controls = {
            "AGGRESSIVE_GROWTH": {
                "allocation_multiplier": 1.12,
                "trade_frequency_multiplier": 1.2,
                "min_confidence_floor": 0.52,
                "allow_evolution": True,
                "allow_compounding": True,
                "risk_tolerance": "high",
                "bucket_bias": {
                    "core_trend": 1.04,
                    "mean_reversion": 0.92,
                    "crypto_momentum": 1.10,
                    "high_risk_sprint": 1.16,
                },
            },
            "BALANCED": {
                "allocation_multiplier": 1.0,
                "trade_frequency_multiplier": 1.0,
                "min_confidence_floor": 0.56,
                "allow_evolution": True,
                "allow_compounding": True,
                "risk_tolerance": "medium",
                "bucket_bias": {
                    "core_trend": 1.02,
                    "mean_reversion": 1.0,
                    "crypto_momentum": 1.0,
                    "high_risk_sprint": 0.96,
                },
            },
            "DEFENSIVE": {
                "allocation_multiplier": 0.82,
                "trade_frequency_multiplier": 0.72,
                "min_confidence_floor": 0.61,
                "allow_evolution": False,
                "allow_compounding": True,
                "risk_tolerance": "low",
                "bucket_bias": {
                    "core_trend": 1.05,
                    "mean_reversion": 1.14,
                    "crypto_momentum": 0.82,
                    "high_risk_sprint": 0.44,
                },
            },
            "SURVIVAL": {
                "allocation_multiplier": 0.58,
                "trade_frequency_multiplier": 0.45,
                "min_confidence_floor": 0.67,
                "allow_evolution": False,
                "allow_compounding": False,
                "risk_tolerance": "minimal",
                "bucket_bias": {
                    "core_trend": 1.06,
                    "mean_reversion": 1.18,
                    "crypto_momentum": 0.60,
                    "high_risk_sprint": 0.20,
                },
            },
        }[mode]

        return {
            "mode": mode,
            "reason": reason,
            "system_confidence": {
                "score": round(confidence_score, 4),
                "label": confidence_label,
            },
            "experiment_instability": experiment_instability,
            "signals": {
                "goal_pressure": round(float(goal_pressure or 1.0), 4),
                "drawdown_pct": round(float(drawdown_pct or 0.0), 4),
                "meta_risk_mode": meta_mode,
                "confidence_collapse": confidence_collapse,
                "correlation_spike": correlation_spike,
            },
            "controls": controls,
        }


system_mode_service = SystemModeService()