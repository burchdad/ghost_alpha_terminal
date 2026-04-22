from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import uuid4

from app.core.config import settings
from app.services.brokers.base import (
    BrokerAdapter,
    BrokerCapabilities,
    BrokerOrderRequest,
    BrokerOrderResult,
    BrokerQuote,
)


class CoinbaseBrokerAdapter(BrokerAdapter):
    """Coinbase Advanced Trade execution adapter."""

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
        if not settings.coinbase_api_key_name or not settings.coinbase_api_private_key:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Coinbase credentials are not configured.",
                error="Missing COINBASE_API_KEY_NAME or COINBASE_API_PRIVATE_KEY",
            )

        if not settings.coinbase_live_trading_enabled:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Coinbase live trading is disabled by configuration.",
                error="Set COINBASE_LIVE_TRADING_ENABLED=true to allow order submission.",
            )

        product_id = self._normalize_product_id(request.symbol)
        if not self._is_product_allowed(product_id):
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason=f"Product {product_id} is not in the Coinbase trading allowlist.",
                error="UnsupportedProduct",
            )

        client = self._new_client()
        if client is None:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Coinbase SDK is unavailable.",
                error="Install dependency coinbase-advanced-py",
            )

        product_check = self._validate_product(client, product_id)
        if product_check is not None:
            return product_check

        funds_check = self._validate_funds(client, request=request, product_id=product_id)
        if funds_check is not None:
            return funds_check

        client_order_id = request.client_order_id or uuid4().hex
        size = self._normalize_size(request.qty)
        if size is None:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Invalid order size.",
                error=f"qty must be > 0, got {request.qty}",
            )

        try:
            if request.order_type == "market":
                if request.side == "buy":
                    response = client.market_order_buy(
                        client_order_id=client_order_id,
                        product_id=product_id,
                        base_size=size,
                    )
                else:
                    response = client.market_order_sell(
                        client_order_id=client_order_id,
                        product_id=product_id,
                        base_size=size,
                    )
            else:
                if request.limit_price is None:
                    return BrokerOrderResult(
                        broker=self.name,
                        submitted=False,
                        order_id=None,
                        reason="Limit orders require a limit_price.",
                        error="Missing limit_price",
                    )
                limit_price = self._normalize_size(request.limit_price)
                if limit_price is None:
                    return BrokerOrderResult(
                        broker=self.name,
                        submitted=False,
                        order_id=None,
                        reason="Invalid limit price.",
                        error=f"limit_price must be > 0, got {request.limit_price}",
                    )

                if request.side == "buy":
                    response = client.limit_order_gtc_buy(
                        client_order_id=client_order_id,
                        product_id=product_id,
                        base_size=size,
                        limit_price=limit_price,
                    )
                else:
                    response = client.limit_order_gtc_sell(
                        client_order_id=client_order_id,
                        product_id=product_id,
                        base_size=size,
                        limit_price=limit_price,
                    )
        except Exception as exc:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason="Broker request failed while submitting order.",
                error=str(exc),
            )

        payload = self._to_dict(response)
        success = bool(payload.get("success"))
        success_response = payload.get("success_response") if isinstance(payload.get("success_response"), dict) else {}
        order_id = payload.get("order_id") or success_response.get("order_id")

        if success:
            return BrokerOrderResult(
                broker=self.name,
                submitted=True,
                order_id=order_id,
                reason=f"Order submitted via {self.name}.",
                raw=payload,
            )

        error_response = payload.get("error_response") if isinstance(payload.get("error_response"), dict) else {}
        failure_reason = payload.get("failure_reason")
        error_message = error_response.get("message") or error_response.get("error_details") or str(failure_reason or "Unknown")
        return BrokerOrderResult(
            broker=self.name,
            submitted=False,
            order_id=order_id,
            reason="Broker rejected order.",
            error=error_message,
            raw=payload,
        )

    def get_quote(self, symbol: str, *, user_id: str | None = None) -> BrokerQuote | None:
        del user_id
        client = self._new_client()
        if client is None:
            return None

        product_id = self._normalize_product_id(symbol)
        try:
            product = client.get_product(product_id=product_id)
            data = self._to_dict(product)
            bid = self._to_float(data.get("best_bid"), 0.0)
            ask = self._to_float(data.get("best_ask"), 0.0)
            last = self._to_float(data.get("price"), 0.0)
            return BrokerQuote(symbol=symbol.upper(), bid=bid, ask=ask, last=last, source=self.name)
        except Exception:
            return None

    def _new_client(self):
        try:
            from coinbase.rest import RESTClient

            return RESTClient(
                api_key=settings.coinbase_api_key_name,
                api_secret=settings.coinbase_api_private_key,
                timeout=10,
            )
        except Exception:
            return None

    def _is_product_allowed(self, product_id: str) -> bool:
        allowlist = {item.strip().upper() for item in settings.coinbase_trade_products.split(",") if item.strip()}
        if not allowlist:
            return True
        return product_id.upper() in allowlist

    def _validate_product(self, client, product_id: str) -> BrokerOrderResult | None:
        try:
            product_data = self._to_dict(client.get_product(product_id=product_id, get_tradability_status=True))
        except Exception as exc:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason=f"Unable to fetch product metadata for {product_id}.",
                error=str(exc),
            )

        if bool(product_data.get("is_disabled", False)):
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason=f"Product {product_id} is disabled.",
                error="ProductDisabled",
            )

        trading_disabled = product_data.get("trading_disabled")
        if trading_disabled is True:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason=f"Product {product_id} is not currently tradable.",
                error="TradingDisabled",
            )
        return None

    def _validate_funds(self, client, *, request: BrokerOrderRequest, product_id: str) -> BrokerOrderResult | None:
        balances = self._load_available_balances(client)
        base_currency, quote_currency = self._split_product_id(product_id)
        size = self._to_float(request.qty, 0.0)

        if request.side == "sell":
            base_available = balances.get(base_currency, 0.0)
            if base_available + 1e-12 < size:
                return BrokerOrderResult(
                    broker=self.name,
                    submitted=False,
                    order_id=None,
                    reason=f"Insufficient {base_currency} balance for sell order.",
                    error=f"available={base_available:.8f} required={size:.8f}",
                )
            return None

        quote_balance = balances.get(quote_currency, 0.0)
        usdc_balance = balances.get("USDC", 0.0)
        effective_quote_balance = quote_balance if quote_currency == "USDC" else max(quote_balance, usdc_balance)

        quote_estimate = self._estimate_quote_notional(client, product_id=product_id, base_size=size)
        if quote_estimate is None:
            return None

        if effective_quote_balance + 1e-12 < quote_estimate:
            return BrokerOrderResult(
                broker=self.name,
                submitted=False,
                order_id=None,
                reason=f"Insufficient {quote_currency}/USDC balance for buy order.",
                error=f"available={effective_quote_balance:.8f} estimated_required={quote_estimate:.8f}",
            )
        return None

    def _estimate_quote_notional(self, client, *, product_id: str, base_size: float) -> float | None:
        try:
            product = self._to_dict(client.get_product(product_id=product_id))
            last_price = self._to_float(product.get("price"), 0.0)
            if last_price <= 0:
                return None
            return last_price * base_size * 1.005
        except Exception:
            return None

    def _load_available_balances(self, client) -> dict[str, float]:
        balances: dict[str, float] = {}
        cursor: str | None = None
        for _ in range(10):
            payload = self._to_dict(client.get_accounts(limit=250, cursor=cursor))
            for account in payload.get("accounts", []):
                account_data = self._to_dict(account)
                if not account_data:
                    continue
                currency = str(account_data.get("currency") or "").upper()
                if not currency:
                    continue
                available = account_data.get("available_balance")
                if isinstance(available, dict):
                    value = self._to_float(available.get("value"), 0.0)
                else:
                    value = self._to_float(available, 0.0)
                balances[currency] = balances.get(currency, 0.0) + value

            has_next = bool(payload.get("has_next", False))
            cursor_value = payload.get("cursor")
            cursor = str(cursor_value) if cursor_value else None
            if not has_next or not cursor:
                break
        return balances

    def _split_product_id(self, product_id: str) -> tuple[str, str]:
        upper = product_id.upper()
        if "-" in upper:
            base, quote = upper.split("-", 1)
            return base, quote
        if upper.endswith("USD") and len(upper) > 3:
            return upper[:-3], "USD"
        return upper, "USD"

    def _normalize_product_id(self, symbol: str) -> str:
        upper = symbol.upper()
        if "-" in upper:
            return upper
        if upper.endswith("USD") and len(upper) > 3:
            return f"{upper[:-3]}-USD"
        return upper

    def _normalize_size(self, value: Any) -> str | None:
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            return None
        if decimal_value <= 0:
            return None
        normalized = decimal_value.normalize()
        text = format(normalized, "f")
        return text.rstrip("0").rstrip(".") if "." in text else text

    def _to_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except Exception:
            return default

    def _to_dict(self, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return value
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            converted = to_dict()
            if isinstance(converted, dict):
                return converted
        raw = getattr(value, "__dict__", None)
        if isinstance(raw, dict):
            return dict(raw)
        return {}


coinbase_broker_adapter = CoinbaseBrokerAdapter()
