from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

import httpx

from app.services.alpaca_client import alpaca_client


class LivePortfolioService:
    def snapshot(self) -> dict | None:
        try:
            account = alpaca_client.get("/v2/account")
            positions = alpaca_client.get("/v2/positions")
        except httpx.HTTPStatusError:
            return None
        except Exception:
            return None

        position_rows = positions if isinstance(positions, list) else [positions]
        active_positions: list[dict] = []
        sector_counter: Counter[str] = Counter()
        strategy_counter: Counter[str] = Counter()
        total_exposure = 0.0

        for position in position_rows:
            symbol = str(position.get("symbol", "")).upper()
            qty = float(position.get("qty") or 0.0)
            market_value = abs(float(position.get("market_value") or 0.0))
            if not symbol or qty == 0:
                continue
            side = "LONG" if qty > 0 else "SHORT"
            strategy = "LIVE_ALPACA"
            sector = self._sector_for_symbol(symbol)
            total_exposure += market_value
            sector_counter[sector] += market_value
            strategy_counter[strategy] += market_value
            active_positions.append(
                {
                    "symbol": symbol,
                    "strategy": strategy,
                    "side": side,
                    "entry_price": float(position.get("avg_entry_price") or 0.0),
                    "units": abs(qty),
                    "notional": market_value,
                    "sector": sector,
                    "opened_at": datetime.now(tz=timezone.utc),
                }
            )

        balance = float(account.get("equity") or account.get("cash") or 0.0)
        buying_power = float(account.get("buying_power") or 0.0)
        return {
            "account_balance": round(balance, 2),
            "active_positions": active_positions,
            "total_exposure": round(total_exposure, 2),
            "risk_exposure_pct": round((total_exposure / balance) if balance > 0 else 0.0, 4),
            "sector_concentration": {k: round(v, 2) for k, v in sector_counter.items()},
            "strategy_exposure": {k: round(v, 2) for k, v in strategy_counter.items()},
            "available_buying_power": round(buying_power, 2),
            "max_concurrent_trades": 8,
        }

    def _sector_for_symbol(self, symbol: str) -> str:
        mapping = {
            "AAPL": "TECH",
            "MSFT": "TECH",
            "NVDA": "TECH",
            "AMD": "TECH",
            "TSLA": "AUTO",
            "SPY": "INDEX",
        }
        return mapping.get(symbol.upper(), "OTHER")


live_portfolio_service = LivePortfolioService()
