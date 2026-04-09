from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock


@dataclass
class Position:
    symbol: str
    strategy: str
    side: str
    entry_price: float
    units: float
    notional: float
    sector: str
    opened_at: datetime


class PortfolioManager:
    def __init__(self) -> None:
        self._lock = Lock()
        self._balance = 100000.0
        self._max_concurrent_trades = 8
        self._positions: list[Position] = []

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

    def configure(self, *, balance: float | None = None, max_concurrent_trades: int | None = None) -> None:
        with self._lock:
            if balance is not None and balance > 0:
                self._balance = balance
            if max_concurrent_trades is not None and max_concurrent_trades >= 1:
                self._max_concurrent_trades = max_concurrent_trades

    def can_open_position(self, *, symbol: str, notional: float) -> tuple[bool, str]:
        with self._lock:
            if len(self._positions) >= self._max_concurrent_trades:
                return False, "Max concurrent trades reached"

            total_exposure = sum(pos.notional for pos in self._positions)
            if total_exposure + notional > self._balance * 2.0:
                return False, "Total exposure limit reached"

            sector = self._sector_for_symbol(symbol)
            sector_exposure = sum(pos.notional for pos in self._positions if pos.sector == sector)
            if sector_exposure + notional > self._balance * 0.6:
                return False, "Sector concentration too high"

            return True, ""

    def open_position(
        self,
        *,
        symbol: str,
        strategy: str,
        side: str,
        entry_price: float,
        units: float,
    ) -> dict:
        notional = entry_price * units
        ok, reason = self.can_open_position(symbol=symbol, notional=notional)
        if not ok:
            return {"accepted": False, "reason": reason}

        position = Position(
            symbol=symbol.upper(),
            strategy=strategy,
            side=side,
            entry_price=entry_price,
            units=units,
            notional=notional,
            sector=self._sector_for_symbol(symbol),
            opened_at=datetime.now(tz=timezone.utc),
        )
        with self._lock:
            self._positions.append(position)

        return {"accepted": True, "position": position}

    def snapshot(self) -> dict:
        with self._lock:
            total_exposure = sum(p.notional for p in self._positions)
            sector_counts = Counter([p.sector for p in self._positions])
            allocation = {
                sector: round(sum(p.notional for p in self._positions if p.sector == sector), 2)
                for sector in sector_counts
            }
            return {
                "account_balance": round(self._balance, 2),
                "active_positions": [
                    {
                        "symbol": p.symbol,
                        "strategy": p.strategy,
                        "side": p.side,
                        "entry_price": round(p.entry_price, 4),
                        "units": round(p.units, 2),
                        "notional": round(p.notional, 2),
                        "sector": p.sector,
                        "opened_at": p.opened_at,
                    }
                    for p in self._positions
                ],
                "total_exposure": round(total_exposure, 2),
                "risk_exposure_pct": round((total_exposure / self._balance) if self._balance > 0 else 0.0, 4),
                "sector_concentration": allocation,
                "max_concurrent_trades": self._max_concurrent_trades,
            }


portfolio_manager = PortfolioManager()
