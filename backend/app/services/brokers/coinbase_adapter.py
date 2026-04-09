from __future__ import annotations

from app.core.config import settings
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
        keys_present = bool(settings.coinbase_api_key_name and settings.coinbase_api_private_key)
        return BrokerOrderResult(
            broker=self.name,
            submitted=False,
            order_id=None,
            reason=(
                "Coinbase credentials detected but adapter signing/execution path is not activated yet."
                if keys_present
                else "Coinbase adapter is not activated and API keys are not configured."
            ),
            error="NotImplemented",
        )

    def get_quote(self, symbol: str) -> BrokerQuote | None:
        return None


coinbase_broker_adapter = CoinbaseBrokerAdapter()
