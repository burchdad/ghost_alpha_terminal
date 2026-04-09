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
    realized_volatility_pct: float = 0.02


class CapitalAllocator:
    def compute(self, payload: AllocationInput) -> dict:
        confidence = max(0.0, min(payload.confidence, 1.0))
        agreement = max(0.0, min(payload.agent_agreement, 1.0))
        drawdown_pct = max(0.0, min(payload.drawdown_pct, 1.0))
        exposure_pct = max(0.0, min(payload.current_exposure_pct, 1.0))
        realized_vol = max(0.0005, min(payload.realized_volatility_pct, 1.0))
        price = max(payload.current_price, 0.01)
        balance = max(payload.account_balance, 0.0)

        confidence_edge = max(0.0, confidence - 0.50)
        confidence_scalar = min((confidence_edge / 0.45) ** 1.15 if confidence_edge > 0 else 0.0, 1.0)

        risk_multiplier = {
            "LOW": 1.0,
            "MEDIUM": 0.72,
            "HIGH": 0.50,
        }.get(payload.risk_level, 0.60)

        regime_multiplier = {
            "TRENDING": 1.00,
            "RANGE_BOUND": 0.82,
            "HIGH_VOLATILITY": 0.58,
        }.get(payload.regime, 0.75)

        target_vol = {
            "TRENDING": 0.020,
            "RANGE_BOUND": 0.016,
            "HIGH_VOLATILITY": 0.012,
        }.get(payload.regime, 0.016)
        volatility_multiplier = max(0.35, min(target_vol / realized_vol, 1.30))

        assumed_rr = {
            "LOW": 2.0,
            "MEDIUM": 1.6,
            "HIGH": 1.25,
        }.get(payload.risk_level, 1.5)
        p = confidence
        q = 1.0 - p
        kelly_fraction = max(0.0, min((assumed_rr * p - q) / assumed_rr, 0.20))

        agreement_multiplier = 0.75 + (agreement * 0.50)
        drawdown_multiplier = max(0.20, 1.0 - (drawdown_pct * 3.2))
        portfolio_risk_multiplier = max(0.15, 1.0 - (exposure_pct * 1.3))

        max_position_pct = 0.12
        kelly_target = kelly_fraction * 0.50
        confidence_target = confidence_scalar * max_position_pct
        target_pct = max(kelly_target, confidence_target)
        target_pct *= risk_multiplier
        target_pct *= regime_multiplier
        target_pct *= volatility_multiplier
        target_pct *= agreement_multiplier
        target_pct *= drawdown_multiplier
        target_pct *= portfolio_risk_multiplier
        target_pct = max(0.0, min(target_pct, max_position_pct))

        notional = round(balance * target_pct, 2)
        qty = round(notional / price, 4) if price > 0 else 0.0
        stop_loss_pct = {
            "LOW": 0.018,
            "MEDIUM": 0.026,
            "HIGH": 0.035,
        }.get(payload.risk_level, 0.028)
        stop_loss_pct = min(0.05, max(0.01, stop_loss_pct + realized_vol * 0.25))
        max_loss_amount = round(notional * stop_loss_pct, 2)
        accepted = qty >= 0.0001 and notional >= 10.0 and confidence >= 0.53 and target_pct >= 0.001

        rationale = [
            f"confidence_scalar={confidence_scalar:.3f}",
            f"kelly_fraction={kelly_fraction:.3f}",
            f"risk_mult={risk_multiplier:.2f}",
            f"regime_mult={regime_multiplier:.2f}",
            f"volatility_mult={volatility_multiplier:.2f}",
            f"agreement_mult={agreement_multiplier:.2f}",
            f"drawdown_mult={drawdown_multiplier:.2f}",
            f"portfolio_risk_mult={portfolio_risk_multiplier:.2f}",
        ]

        return {
            "accepted": accepted,
            "target_pct": round(target_pct, 6),
            "recommended_notional": notional,
            "recommended_qty": qty,
            "max_risk_amount": max_loss_amount,
            "stop_loss_pct": stop_loss_pct,
            "agent_agreement": round(agreement, 4),
            "realized_volatility_pct": round(realized_vol, 6),
            "kelly_fraction": round(kelly_fraction, 6),
            "rationale": rationale,
            "reason": "Allocation approved." if accepted else "Allocation rejected: confidence/notional below threshold.",
        }


capital_allocator = CapitalAllocator()