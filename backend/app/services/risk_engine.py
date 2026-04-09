from __future__ import annotations


class RiskEngine:
    def evaluate_trade(
        self,
        *,
        entry_price: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        confidence: float,
        max_loss_amount: float,
        account_balance: float,
    ) -> dict:
        risk_per_unit = entry_price * stop_loss_pct
        reward_per_unit = entry_price * take_profit_pct
        rr_ratio = reward_per_unit / risk_per_unit if risk_per_unit > 0 else 0.0

        prob_win = max(0.35, min(0.9, confidence))
        prob_loss = 1 - prob_win
        expected_value = prob_win * reward_per_unit - prob_loss * risk_per_unit

        max_loss_pct_of_balance = (max_loss_amount / account_balance) if account_balance > 0 else 1.0

        approved = True
        rejection_reason = ""
        if max_loss_pct_of_balance > 0.025:
            approved = False
            rejection_reason = "Risk per trade exceeds account limits."
        elif rr_ratio < 1.1:
            approved = False
            rejection_reason = "Risk/reward ratio is too weak."
        elif expected_value <= 0:
            approved = False
            rejection_reason = "Expected value is non-positive."

        if not approved:
            risk_level = "HIGH"
        elif max_loss_pct_of_balance > 0.015 or rr_ratio < 1.5:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "approved": approved,
            "risk_reward_ratio": round(rr_ratio, 3),
            "max_loss_amount": round(max_loss_amount, 2),
            "expected_value": round(expected_value, 4),
            "risk_level": risk_level,
            "reason": rejection_reason,
        }


risk_engine = RiskEngine()
