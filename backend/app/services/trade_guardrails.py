from __future__ import annotations


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
        if confidence < 0.60:
            return False, "Rejected by guardrails: swarm confidence below 60%."
        if expected_value <= 0:
            return False, "Rejected by guardrails: expected value is non-positive."
        if risk_reward_ratio < 1.5:
            return False, "Rejected by guardrails: risk/reward ratio below 1.5."

        max_units = 2000
        if position_size > max_units:
            return False, "Rejected by guardrails: position size exceeds max unit threshold."

        if position_notional > account_balance * 0.2:
            return False, "Rejected by guardrails: position notional exceeds 20% balance threshold."

        return True, ""


trade_guardrails = TradeGuardrails()
