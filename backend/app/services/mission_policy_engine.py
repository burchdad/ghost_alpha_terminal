from __future__ import annotations

from typing import Literal


MissionStyle = Literal["capital_preservation", "balanced_growth", "sprint", "recovery"]


class MissionPolicyEngine:
    @staticmethod
    def risk_posture(drawdown_pct: float) -> dict:
        dd = max(0.0, float(drawdown_pct or 0.0))
        # Drawdown behavior switching:
        # X -> force recovery mode, Y -> capital preservation only.
        if dd >= 0.10:
            return {
                "mode": "capital_preservation_only",
                "forced_style": "capital_preservation",
                "reason": "drawdown >= 10%",
            }
        if dd >= 0.06:
            return {
                "mode": "recovery_forced",
                "forced_style": "recovery",
                "reason": "drawdown >= 6%",
            }
        return {
            "mode": "normal",
            "forced_style": None,
            "reason": "drawdown below forced-switch thresholds",
        }

    def resolve_style(
        self,
        *,
        goal_pressure: float,
        stress_level: str,
        drawdown_pct: float,
    ) -> MissionStyle:
        posture = self.risk_posture(drawdown_pct)
        forced = posture.get("forced_style")
        if forced in {"capital_preservation", "recovery", "balanced_growth", "sprint"}:
            return forced
        if drawdown_pct >= 0.08:
            return "recovery"
        if goal_pressure >= 1.80 or stress_level.upper() == "EXTREME":
            return "sprint"
        if goal_pressure <= 0.95 and drawdown_pct <= 0.025:
            return "capital_preservation"
        return "balanced_growth"

    def tuning(self, *, style: MissionStyle, sprint_active: bool) -> dict:
        base: dict[MissionStyle, dict] = {
            "capital_preservation": {
                "concurrency_target": 6,
                "per_trade_cap_pct": 0.12,
                "min_confidence_floor": 0.61,
                "crypto_bias": 0.22,
                "allow_high_risk_sprint": False,
            },
            "balanced_growth": {
                "concurrency_target": 10,
                "per_trade_cap_pct": 0.20,
                "min_confidence_floor": 0.56,
                "crypto_bias": 0.30,
                "allow_high_risk_sprint": False,
            },
            "sprint": {
                "concurrency_target": 12,
                "per_trade_cap_pct": 0.24,
                "min_confidence_floor": 0.52,
                "crypto_bias": 0.38,
                "allow_high_risk_sprint": True,
            },
            "recovery": {
                "concurrency_target": 5,
                "per_trade_cap_pct": 0.10,
                "min_confidence_floor": 0.64,
                "crypto_bias": 0.18,
                "allow_high_risk_sprint": False,
            },
        }[style].copy()
        if style == "capital_preservation":
            base["per_trade_cap_pct"] = min(float(base["per_trade_cap_pct"]), 0.10)
            base["min_confidence_floor"] = max(float(base["min_confidence_floor"]), 0.64)
            base["allow_high_risk_sprint"] = False
        base["sprint_active"] = bool(sprint_active)
        return base

    def capital_buckets(
        self,
        *,
        style: MissionStyle,
        dominant_regime: str,
        regime_quality: dict,
        bucket_quality: dict | None = None,
    ) -> dict[str, float]:
        buckets: dict[MissionStyle | str, dict[str, float]] = {
            "capital_preservation": {
                "core_trend": 0.30,
                "mean_reversion": 0.40,
                "crypto_momentum": 0.20,
                "high_risk_sprint": 0.10,
            },
            "balanced_growth": {
                "core_trend": 0.34,
                "mean_reversion": 0.30,
                "crypto_momentum": 0.26,
                "high_risk_sprint": 0.10,
            },
            "sprint": {
                "core_trend": 0.28,
                "mean_reversion": 0.18,
                "crypto_momentum": 0.30,
                "high_risk_sprint": 0.24,
            },
            "recovery": {
                "core_trend": 0.25,
                "mean_reversion": 0.45,
                "crypto_momentum": 0.20,
                "high_risk_sprint": 0.10,
            },
        }
        weights = dict(buckets[style])

        regime = (dominant_regime or "").upper()
        if regime == "TRENDING":
            weights["core_trend"] += 0.06
            weights["mean_reversion"] -= 0.03
        elif regime == "RANGE_BOUND":
            weights["mean_reversion"] += 0.07
            weights["core_trend"] -= 0.03
        elif regime == "HIGH_VOLATILITY":
            weights["crypto_momentum"] += 0.05
            weights["high_risk_sprint"] += 0.03
            weights["mean_reversion"] -= 0.04

        hv_quality = float((regime_quality.get("HIGH_VOLATILITY") or {}).get("quality_score", 0.5) or 0.5)
        if hv_quality < 0.45:
            weights["high_risk_sprint"] = max(0.05, weights["high_risk_sprint"] - 0.05)
            weights["mean_reversion"] += 0.03
            weights["core_trend"] += 0.02

        # Capital reallocation engine: shift weight from losing buckets to winning buckets.
        if bucket_quality:
            for bucket, stats in bucket_quality.items():
                if bucket not in weights:
                    continue
                q = float((stats or {}).get("quality_score", 0.5) or 0.5)
                adjustment = max(-0.05, min((q - 0.5) * 0.20, 0.05))
                weights[bucket] = max(0.05, weights[bucket] + adjustment)

        total = sum(max(v, 0.01) for v in weights.values())
        normalized = {k: round(max(v, 0.01) / total, 4) for k, v in weights.items()}
        return normalized

    def mission_snapshot(
        self,
        *,
        goal_status: dict,
        drawdown_pct: float,
        sprint_active: bool,
        dominant_regime: str,
        regime_quality: dict,
        bucket_quality: dict | None = None,
    ) -> dict:
        goal_pressure = float(goal_status.get("goal_pressure_multiplier", 1.0) or 1.0)
        stress_level = str(goal_status.get("stress_level", "LOW") or "LOW")
        style = self.resolve_style(goal_pressure=goal_pressure, stress_level=stress_level, drawdown_pct=drawdown_pct)
        posture = self.risk_posture(drawdown_pct)
        tuning = self.tuning(style=style, sprint_active=sprint_active)
        buckets = self.capital_buckets(
            style=style,
            dominant_regime=dominant_regime,
            regime_quality=regime_quality,
            bucket_quality=bucket_quality,
        )

        return {
            "mission_style": style,
            "risk_posture": posture,
            "goal_pressure_multiplier": round(goal_pressure, 4),
            "stress_level": stress_level,
            "drawdown_pct": round(drawdown_pct, 4),
            "tuning": tuning,
            "capital_buckets": buckets,
        }

    def simulate_scenario(
        self,
        *,
        current_capital: float,
        target_capital: float,
        timeframe_days: int,
    ) -> dict:
        current = max(float(current_capital), 1.0)
        target = max(float(target_capital), 1.0)
        days = max(int(timeframe_days), 1)

        required_total_return = (target / current) - 1.0
        required_daily_return = (target / current) ** (1.0 / days) - 1.0
        pressure = max(0.5, min(required_daily_return / 0.002, 2.5))

        style = self.resolve_style(
            goal_pressure=pressure,
            stress_level="EXTREME" if pressure >= 1.9 else "HIGH" if pressure >= 1.4 else "MEDIUM",
            drawdown_pct=0.0,
        )
        unrealistic = required_daily_return > 0.035
        refusal = required_daily_return > 0.060

        return {
            "current_capital": round(current, 2),
            "target_capital": round(target, 2),
            "timeframe_days": days,
            "required_total_return": round(required_total_return, 6),
            "required_daily_return": round(required_daily_return, 6),
            "implied_goal_pressure": round(pressure, 4),
            "recommended_mission_style": style,
            "target_unrealistic": unrealistic,
            "refuse_activation": refusal,
            "message": (
                "Scenario exceeds defensible daily return threshold; recommend refusing activation."
                if refusal
                else "Scenario is aggressive; sprint policy should activate if accepted."
                if unrealistic
                else "Scenario is within defensible bounds for autonomous execution."
            ),
        }


mission_policy_engine = MissionPolicyEngine()
