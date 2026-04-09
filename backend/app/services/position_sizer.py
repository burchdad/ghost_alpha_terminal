from __future__ import annotations

from math import floor


class PositionSizer:
    def calculate_position_size(
        self,
        account_balance: float,
        risk_per_trade: float,
        stop_loss_pct: float,
        entry_price: float = 1.0,
    ) -> dict[str, float]:
        risk_per_trade = max(0.001, min(risk_per_trade, 0.05))
        stop_loss_pct = max(0.001, min(stop_loss_pct, 0.5))
        entry_price = max(entry_price, 0.01)

        max_loss_amount = account_balance * risk_per_trade
        risk_per_unit = entry_price * stop_loss_pct
        units = floor(max_loss_amount / risk_per_unit) if risk_per_unit > 0 else 0
        position_notional = units * entry_price

        return {
            "position_size": float(max(units, 0)),
            "max_loss_amount": round(max_loss_amount, 2),
            "position_notional": round(position_notional, 2),
        }


position_sizer = PositionSizer()
