from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol


@dataclass
class BrokerCapabilities:
    broker: str
    supports_equities: bool
    supports_crypto: bool
    supports_options: bool
    supports_fractional: bool
    supports_leverage: bool


@dataclass
class BrokerQuote:
    symbol: str
    bid: float
    ask: float
    last: float
    source: str


@dataclass
class BrokerOrderRequest:
    symbol: str
    side: Literal["buy", "sell"]
    qty: float
    asset_class: Literal["equity", "crypto", "option"] = "equity"
    option_symbol: str | None = None
    option_side: Literal["buy_to_open", "buy_to_close", "sell_to_open", "sell_to_close"] | None = None
    order_type: Literal["market", "limit"] = "market"
    time_in_force: Literal["day", "gtc"] = "day"
    limit_price: float | None = None
    client_order_id: str | None = None


@dataclass
class BrokerOrderResult:
    broker: str
    submitted: bool
    order_id: str | None
    reason: str
    error: str | None = None
    raw: dict | None = None


class BrokerAdapter(Protocol):
    name: str

    def capabilities(self) -> BrokerCapabilities: ...

    def submit_order(self, request: BrokerOrderRequest) -> BrokerOrderResult: ...

    def get_quote(self, symbol: str) -> BrokerQuote | None: ...
