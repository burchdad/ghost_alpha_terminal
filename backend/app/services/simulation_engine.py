from __future__ import annotations

from typing import Literal


class SimulationEngine:
    def resolve_trade(
        self,
        *,
        side: Literal["LONG", "SHORT"],
        entry_price: float,
        future_prices: list[float],
        take_profit_pct: float,
        stop_loss_pct: float,
    ) -> tuple[int, float, float]:
        take_level = entry_price * (1 + take_profit_pct if side == "LONG" else 1 - take_profit_pct)
        stop_level = entry_price * (1 - stop_loss_pct if side == "LONG" else 1 + stop_loss_pct)

        for step, price in enumerate(future_prices, start=1):
            if side == "LONG":
                if price >= take_level:
                    pnl = price - entry_price
                    return step, price, pnl
                if price <= stop_level:
                    pnl = price - entry_price
                    return step, price, pnl
            else:
                if price <= take_level:
                    pnl = entry_price - price
                    return step, price, pnl
                if price >= stop_level:
                    pnl = entry_price - price
                    return step, price, pnl

        final_price = future_prices[-1]
        pnl = final_price - entry_price if side == "LONG" else entry_price - final_price
        return len(future_prices), final_price, pnl


simulation_engine = SimulationEngine()
