from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.alpaca_client import alpaca_client
from app.services.brokers.base import (
    BrokerAdapter,
    BrokerCapabilities,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerQuote,
)


class AlpacaBrokerAdapter(BrokerAdapter):
    name = "alpaca"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker=self.name,
            supports_equities=True,
            supports_crypto=True,
            supports_options=False,
            supports_fractional=True,
            supports_leverage=False,
        )

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Alpaca credentials are not configured.",
                error="Missing ALPACA_API_KEY or ALPACA_SECRET_KEY",
            )

        payload: dict[str, str] = {
            "symbol": request.symbol,
            "qty": str(request.qty),
            "side": request.side,
            "type": request.order_type,
            "time_in_force": request.time_in_force,
        }
        if request.client_order_id:
            payload["client_order_id"] = request.client_order_id
        if request.order_type == "limit" and request.limit_price is not None:
            payload["limit_price"] = str(request.limit_price)

        try:
            response = alpaca_client.post("/v2/orders", body=payload, symbol=request.symbol)
            return BrokerOrderResult(
                broker=self.name,
                submitted=True,
                order_id=response.get("id"),
                reason=f"Order submitted via {self.name}.",
                raw=response,
            )
        except httpx.HTTPStatusError as exc:
            message = f"Alpaca HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Broker rejected order.",
                error=message,
            )
        except httpx.RequestError as exc:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Network error while reaching broker.",
                error=str(exc),
            )

    def get_quote(self, symbol: str) -> BrokerQuote | None:
        try:
            latest = alpaca_client.get(f"/v2/stocks/{symbol}/quotes/latest", symbol=symbol)
            quote = latest.get("quote", {})
            bid = float(quote.get("bp", 0.0) or 0.0)
            ask = float(quote.get("ap", 0.0) or 0.0)
            last = (bid + ask) / 2 if bid > 0 and ask > 0 else max(bid, ask)
            return BrokerQuote(symbol=symbol, bid=bid, ask=ask, last=last, source=self.name)
        except Exception:
            return None


alpaca_broker_adapter = AlpacaBrokerAdapter()
