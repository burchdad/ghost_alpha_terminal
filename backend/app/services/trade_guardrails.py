from __future__ import annotations

from app.services.goal_engine import goal_engine
from app.services.mission_policy_engine import mission_policy_engine


class TradeGuardrails:
    def validate(
        self,
        *,
        confidence: float,
        expected_value: float,
        risk_reward_ratio: float,
        position_size: float,
        position_notional: float,
        account_balance: float,
    ) -> tuple[bool, str]:
        goal_status = goal_engine.status(current_capital=account_balance)
        mission = mission_policy_engine.mission_snapshot(
            goal_status=goal_status,
            drawdown_pct=0.0,
            sprint_active=False,
            dominant_regime="RANGE_BOUND",
            regime_quality={},
        )
        confidence_floor = float((mission.get("tuning") or {}).get("min_confidence_floor", 0.60) or 0.60)
        if confidence < confidence_floor:
            return False, f"Rejected by guardrails: swarm confidence below {confidence_floor:.2f}."
        if expected_value <= 0:
            return False, "Rejected by guardrails: expected value is non-positive."
        if risk_reward_ratio < 1.5:
            return False, "Rejected by guardrails: risk/reward ratio below 1.5."

        max_units = 2000
        if position_size > max_units:
            return False, "Rejected by guardrails: position size exceeds max unit threshold."

        if position_notional > account_balance * 0.24:
            return False, "Rejected by guardrails: position notional exceeds 24% balance threshold."

        return True, ""


trade_guardrails = TradeGuardrails()
