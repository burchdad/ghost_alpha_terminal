from __future__ import annotations

import httpx

from app.core.config import settings
from app.services.brokers.base import (
    BrokerAdapter,
    BrokerCapabilities,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerQuote,
)
from app.services.tradier_client import tradier_client


class TradierBrokerAdapter(BrokerAdapter):
    """Tradier execution adapter for US equities and options."""

    name = "tradier"

    def capabilities(self) -> BrokerCapabilities:
        return BrokerCapabilities(
            broker=self.name,
            supports_equities=True,
            supports_crypto=False,
            supports_options=True,
            supports_fractional=False,
            supports_leverage=False,
        )

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult:
        if not tradier_client.is_configured():
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Tradier credentials are not configured.",
                error="Missing active Tradier API key/account number for current TRADIER_SANDBOX mode",
            )

        if not settings.tradier_live_trading_enabled:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Tradier live trading is disabled by configuration.",
                error="Set TRADIER_LIVE_TRADING_ENABLED=true to allow order submission.",
            )

        data: dict[str, str] = {
            "class": "option" if request.asset_class == "option" else "equity",
            "symbol": (request.option_symbol or request.symbol).upper(),
            "side": request.option_side or request.side,
            "quantity": str(max(request.qty, 0.0)),
            "type": request.order_type,
            "duration": request.time_in_force,
        }
        if request.asset_class == "option" and request.option_symbol:
            data["option_symbol"] = request.option_symbol.upper()
        if request.order_type == "limit" and request.limit_price is not None:
            data["price"] = str(request.limit_price)

        try:
            payload = tradier_client.post_form(
                f"/accounts/{settings.tradier_effective_account_number}/orders",
                data=data,
            )
        except httpx.HTTPStatusError as exc:
            message = f"Tradier HTTP {exc.response.status_code}: {exc.response.text[:240]}"
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

        order_block = payload.get("order", {}) if isinstance(payload, dict) else {}
        order_id = order_block.get("id") if isinstance(order_block, dict) else None
        if order_id:
            return BrokerOrderResult(
                broker=self.name,
                submitted=True,
                order_id=str(order_id),
                reason=f"Order submitted via {self.name}.",
                raw=payload,
            )

        return BrokerOrderResult(
            broker=self.name,
            submitted=False,
            order_id=None,
            reason="Broker did not confirm order submission.",
            error=str(payload),
            raw=payload if isinstance(payload, dict) else None,
        )

    def get_quote(self, symbol: str) -> BrokerQuote | None:
        try:
            payload = tradier_client.get(
                "/markets/quotes",
                params={"symbols": symbol.upper(), "greeks": "false"},
            )
            quotes = payload.get("quotes", {}) if isinstance(payload, dict) else {}
            quote = quotes.get("quote") if isinstance(quotes, dict) else None
            if isinstance(quote, list):
                quote = quote[0] if quote else None
            if not isinstance(quote, dict):
                return None

            bid = float(quote.get("bid") or 0.0)
            ask = float(quote.get("ask") or 0.0)
            last = float(quote.get("last") or 0.0)
            if last <= 0 and bid > 0 and ask > 0:
                last = (bid + ask) / 2
            return BrokerQuote(symbol=symbol.upper(), bid=bid, ask=ask, last=last, source=self.name)
        except Exception:
            return None


tradier_broker_adapter = TradierBrokerAdapter()
