from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GovernorDecision:
    decision: str  # ALLOW | RESIZE | BLOCK
    adjusted_notional: float
    adjusted_qty: float
    reason: str


class PortfolioRiskGovernor:
    """Final portfolio-level gate before execution."""

    def evaluate(
        self,
        *,
        symbol: str,
        proposed_notional: float,
        proposed_qty: float,
        account_balance: float,
        current_exposure_pct: float,
        drawdown_pct: float,
        sector_concentration: dict[str, float],
    ) -> GovernorDecision:
        max_trade_pct = 0.18
        max_exposure_pct = 0.95
        max_sector_pct = 0.55

        trade_pct = (proposed_notional / max(account_balance, 1.0)) if account_balance > 0 else 1.0

        if drawdown_pct >= 0.10:
            return GovernorDecision(
                decision="BLOCK",
                adjusted_notional=0.0,
                adjusted_qty=0.0,
                reason="Governor blocked trade: rolling drawdown is above 10% cap.",
            )

        if current_exposure_pct >= max_exposure_pct:
            return GovernorDecision(
                decision="BLOCK",
                adjusted_notional=0.0,
                adjusted_qty=0.0,
                reason="Governor blocked trade: portfolio exposure cap reached.",
            )

        if sector_concentration:
            max_sector_notional = max(sector_concentration.values())
            if max_sector_notional / max(account_balance, 1.0) > max_sector_pct:
                return GovernorDecision(
                    decision="BLOCK",
                    adjusted_notional=0.0,
                    adjusted_qty=0.0,
                    reason="Governor blocked trade: sector concentration exceeds cap.",
                )

        if trade_pct <= max_trade_pct:
            return GovernorDecision(
                decision="ALLOW",
                adjusted_notional=round(proposed_notional, 2),
                adjusted_qty=round(proposed_qty, 4),
                reason="Governor approved trade within portfolio risk limits.",
            )

        resized_notional = account_balance * max_trade_pct
        resize_ratio = resized_notional / max(proposed_notional, 1e-6)
        resized_qty = proposed_qty * resize_ratio
        return GovernorDecision(
            decision="RESIZE",
            adjusted_notional=round(resized_notional, 2),
            adjusted_qty=round(resized_qty, 4),
            reason="Governor resized trade to max per-trade notional cap.",
        )


portfolio_risk_governor = PortfolioRiskGovernor()
