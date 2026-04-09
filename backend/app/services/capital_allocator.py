from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AllocationInput:
    account_balance: float
    current_price: float
    confidence: float
    regime: str
    risk_level: str
    agent_agreement: float
    drawdown_pct: float
    current_exposure_pct: float


class CapitalAllocator:
    def compute(self, payload: AllocationInput) -> dict:
        confidence = max(0.0, min(payload.confidence, 1.0))
        agreement = max(0.0, min(payload.agent_agreement, 1.0))
        drawdown_pct = max(0.0, min(payload.drawdown_pct, 1.0))
        exposure_pct = max(0.0, min(payload.current_exposure_pct, 1.0))
        price = max(payload.current_price, 0.01)
        balance = max(payload.account_balance, 0.0)

        if confidence >= 0.75:
            base_pct = 0.08
        elif confidence >= 0.65:
            base_pct = 0.05
        elif confidence >= 0.55:
            base_pct = 0.025
        else:
            base_pct = 0.01

        risk_multiplier = {
            "LOW": 1.0,
            "MEDIUM": 0.65,
            "HIGH": 0.35,
        }.get(payload.risk_level, 0.5)

        regime_multiplier = {
            "TRENDING": 1.0,
            "RANGE_BOUND": 0.85,
            "HIGH_VOLATILITY": 0.55,
        }.get(payload.regime, 0.75)

        agreement_multiplier = 0.7 + (agreement * 0.6)
        drawdown_multiplier = max(0.25, 1.0 - (drawdown_pct * 4.0))
        exposure_multiplier = max(0.25, 1.0 - exposure_pct)

        target_pct = base_pct * risk_multiplier * regime_multiplier * agreement_multiplier
        target_pct *= drawdown_multiplier * exposure_multiplier
        target_pct = max(0.0, min(target_pct, 0.10))

        notional = round(balance * target_pct, 2)
        qty = round(notional / price, 4) if price > 0 else 0.0
        stop_loss_pct = 0.02 if payload.risk_level == "LOW" else 0.03 if payload.risk_level == "MEDIUM" else 0.04
        max_loss_amount = round(notional * stop_loss_pct, 2)
        accepted = qty >= 0.0001 and notional >= 10.0 and confidence >= 0.55

        rationale = [
            f"base={base_pct:.3f}",
            f"risk_mult={risk_multiplier:.2f}",
            f"regime_mult={regime_multiplier:.2f}",
            f"agreement_mult={agreement_multiplier:.2f}",
            f"drawdown_mult={drawdown_multiplier:.2f}",
            f"exposure_mult={exposure_multiplier:.2f}",
        ]

        return {
            "accepted": accepted,
            "target_pct": round(target_pct, 6),
            "recommended_notional": notional,
            "recommended_qty": qty,
            "max_risk_amount": max_loss_amount,
            "stop_loss_pct": stop_loss_pct,
            "agent_agreement": round(agreement, 4),
            "rationale": rationale,
            "reason": "Allocation approved." if accepted else "Allocation rejected: confidence/notional below threshold.",
        }


capital_allocator = CapitalAllocator()