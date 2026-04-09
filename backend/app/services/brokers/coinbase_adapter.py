from __future__ import annotations

from app.services.brokers.base import (
    BrokerAdapter,
    BrokerCapabilities,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerQuote,
)


class CoinbaseBrokerAdapter(BrokerAdapter):
    """Stub adapter to establish the multi-broker interface.

    This is intentionally non-executing until credentials and signing flow are added.
    """

    name = "coinbase"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker=self.name,
            supports_equities=False,
            supports_crypto=True,
            supports_options=False,
            supports_fractional=True,
            supports_leverage=False,
        )

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        return BrokerOrderResult(
            broker=self.name,
            submitted=False,
            order_id=None,
            reason="Coinbase adapter is not activated yet.",
            error="NotImplemented",
        )

    def get_quote(self, symbol: str) -> BrokerQuote | None:
        return None


coinbase_broker_adapter = CoinbaseBrokerAdapter()
