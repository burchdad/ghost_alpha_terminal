from __future__ import annotations

from app.core.config import settings
from app.services.brokers.alpaca_adapter import alpaca_broker_adapter
from app.services.brokers.base import BrokerAdapter, BrokerOrderRequest, BrokerOrderResult
from app.services.brokers.coinbase_adapter import coinbase_broker_adapter
from app.services.brokers.tradier_adapter import tradier_broker_adapter

# Planned broker integrations — OAuth applications in-flight or not yet submitted.
# These are surfaced in the UI as "Integration Planned" to track pipeline status.
PLANNED_BROKERS: dict[str, dict] = {
    "schwab": {
        "label": "Charles Schwab",
        "supports_equities": True,
        "supports_crypto": False,
        "supports_options": True,
        "supports_fractional": True,
        "supports_leverage": False,
        "planned": True,
        "oauth_url": "https://developer.schwab.com",
        "notes": "Full-service broker with an OAuth developer API. Requires approval at developer.schwab.com.",
    },
    "tastytrade": {
        "label": "tastytrade",
        "supports_equities": True,
        "supports_crypto": False,
        "supports_options": True,
        "supports_fractional": False,
        "supports_leverage": True,
        "planned": True,
        "oauth_url": "https://developer.tastytrade.com",
        "notes": "Options- and futures-focused broker with an open REST API. Apply at developer.tastytrade.com.",
    },
    "robinhood": {
        "label": "Robinhood",
        "supports_equities": True,
        "supports_crypto": True,
        "supports_options": True,
        "supports_fractional": True,
        "supports_leverage": False,
        "planned": True,
        "oauth_url": "https://robinhood.com/about/developer-api",
        "notes": "Commission-free equities, crypto, and options with an OAuth developer API program.",
    },
    "tradestation": {
        "label": "TradeStation",
        "supports_equities": True,
        "supports_crypto": False,
        "supports_options": True,
        "supports_fractional": False,
        "supports_leverage": True,
        "planned": True,
        "oauth_url": "https://api.tradestation.com",
        "notes": "Equities, options, and futures broker. OAuth developer access available at api.tradestation.com.",
    },
}


class BrokerRouter:
    def __init__(self) -> None:
        self._adapters: dict[str, BrokerAdapter] = {
            "alpaca": alpaca_broker_adapter,
            "coinbase": coinbase_broker_adapter,
            "tradier": tradier_broker_adapter,
        }

    def capabilities_map(self) -> dict[str, dict]:
        result: dict[str, dict] = {
            name: adapter.capabilities().__dict__
            for name, adapter in self._adapters.items()
        }
        result.update(PLANNED_BROKERS)
        return result

    def classify_asset_type(self, symbol: str) -> str:
        upper = symbol.upper()
        if upper.endswith("USD") and len(upper) <= 10:
            return "crypto"
        return "equity"

    def route_broker(self, *, symbol: str, liquidity_score: float = 1.0, mode: str | None = None) -> str:
        del liquidity_score
        asset_type = self.classify_asset_type(symbol)
        if asset_type == "crypto":
            if (
                mode == "LIVE_TRADING"
                and settings.coinbase_live_trading_enabled
                and settings.coinbase_api_key_name
                and settings.coinbase_api_private_key
            ):
                return "coinbase"

            # Prefer Coinbase for explicitly allowlisted crypto products.
            upper = symbol.upper()
            normalized = f"{upper[:-3]}-USD" if upper.endswith("USD") and len(upper) > 3 else upper
            allowlist = {item.strip().upper() for item in settings.coinbase_trade_products.split(",") if item.strip()}
            if normalized in allowlist:
                return "coinbase"
            return "alpaca"

        if (
            mode == "LIVE_TRADING"
            and settings.tradier_live_trading_enabled
            and settings.tradier_effective_api_key
            and settings.tradier_effective_account_number
        ):
            return "tradier"

        return "alpaca"

    def submit(self, *, request: BrokerOrderRequest, liquidity_score: float = 1.0) -> BrokerOrderResult:
        broker_name = self.route_broker(symbol=request.symbol, liquidity_score=liquidity_score)
        adapter = self._adapters[broker_name]
        return adapter.submit_order(request)


broker_router = BrokerRouter()
