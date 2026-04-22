from __future__ import annotations

import httpx

from app.services.brokers.base import (
    BrokerAdapter,
    BrokerCapabilities,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerQuote,
)
from app.services.schwab_client import schwab_client


class SchwabBrokerAdapter(BrokerAdapter):
    name = "schwab"

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
        if not request.user_id:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Schwab execution requires a connected authenticated user context.",
                error="Missing user_id for Schwab OAuth order submission.",
            )

        if not schwab_client.is_connected(user_id=request.user_id):
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="No connected Schwab account is available.",
                error="Connect a Schwab OAuth account before using Schwab execution.",
            )

        try:
            payload = schwab_client.submit_order(
                symbol=request.option_symbol or request.symbol,
                side=request.option_side or request.side,
                quantity=max(int(round(request.qty)), 1),
                asset_class=request.asset_class,
                account_hash=request.account_id,
                order_type=request.order_type,
                duration=request.time_in_force,
                limit_price=request.limit_price,
                client_order_id=request.client_order_id,
                user_id=request.user_id,
            )
        except httpx.HTTPStatusError as exc:
            message = f"Schwab HTTP {exc.response.status_code}: {exc.response.text[:240]}"
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Broker rejected order.",
                error=message,
            )
        except (RuntimeError, ValueError) as exc:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason=str(exc),
                error=str(exc),
            )
        except httpx.RequestError as exc:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Network error while reaching broker.",
                error=str(exc),
            )

        order_id = None
        location = str(payload.get("location", "") or "")
        if location:
            order_id = location.rstrip("/").split("/")[-1]

        return BrokerOrderResult(
            broker=self.name,
            submitted=True,
            order_id=order_id,
            reason=f"Order submitted via {self.name}.",
            raw=payload,
        )

    def get_quote(self, symbol: str, *, user_id: str | None = None) -> BrokerQuote | None:
        if not schwab_client.is_connected(user_id=user_id):
            return None

        try:
            payload = schwab_client.get_quote(symbol, user_id=user_id)
            quote_block = payload.get("quote") if isinstance(payload.get("quote"), dict) else payload
            bid = float(quote_block.get("bidPrice") or quote_block.get("bid") or 0.0)
            ask = float(quote_block.get("askPrice") or quote_block.get("ask") or 0.0)
            last = float(
                quote_block.get("lastPrice")
                or quote_block.get("mark")
                or quote_block.get("closePrice")
                or 0.0
            )
            if last <= 0 and bid > 0 and ask > 0:
                last = (bid + ask) / 2
            return BrokerQuote(symbol=symbol.upper(), bid=bid, ask=ask, last=last, source=self.name)
        except Exception:
            return None


schwab_broker_adapter = SchwabBrokerAdapter()
