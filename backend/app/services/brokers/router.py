from __future__ import annotations

from app.services.brokers.alpaca_adapter import alpaca_broker_adapter
from app.services.brokers.base import BrokerAdapter, BrokerOrderRequest, BrokerOrderResult
from app.services.brokers.coinbase_adapter import coinbase_broker_adapter


class BrokerRouter:
    def __init__(self) -> None:
        self._adapters: dict[str, BrokerAdapter] = {
            "alpaca": alpaca_broker_adapter,
            "coinbase": coinbase_broker_adapter,
        }

    def capabilities_map(self) -> dict[str, dict]:
        return {
            name: adapter.capabilities().__dict__
            for name, adapter in self._adapters.items()
        }

    def classify_asset_type(self, symbol: str) -> str:
        upper = symbol.upper()
        if upper.endswith("USD") and len(upper) <= 10:
            return "crypto"
        return "equity"

    def route_broker(self, *, symbol: str, liquidity_score: float = 1.0) -> str:
        asset_type = self.classify_asset_type(symbol)
        if asset_type == "crypto":
            if liquidity_score >= 0.55:
                return "coinbase"
            return "alpaca"
        return "alpaca"

    def submit(self, *, request: BrokerOrderRequest, liquidity_score: float = 1.0) -> BrokerOrderResult:
        broker_name = self.route_broker(symbol=request.symbol, liquidity_score=liquidity_score)
        adapter = self._adapters[broker_name]
        return adapter.submit_order(request)


broker_router = BrokerRouter()
