from __future__ import annotations

import json
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

import websocket

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ProductState:
    product_id: str
    last_price: float | None = None
    price_change_pct_24h: float = 0.0
    volume_24h: float = 0.0
    last_update: datetime | None = None
    trades_60s: deque[tuple[datetime, float]] = field(default_factory=lambda: deque(maxlen=2000))


class CoinbaseWsService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._enabled = bool(settings.coinbase_ws_enabled)
        self._url = settings.coinbase_ws_url
        self._products = [p.strip().upper() for p in settings.coinbase_ws_products.split(",") if p.strip()]
        self._states: dict[str, ProductState] = {p: ProductState(product_id=p) for p in self._products}
        self._thread: threading.Thread | None = None
        self._running = False
        self._connected = False
        self._last_error: str | None = None
        self._last_message_at: datetime | None = None

    def start(self) -> None:
        if not self._enabled:
            logger.info("coinbase_ws_disabled")
            return
        with self._lock:
            if self._running:
                return
            self._running = True
        self._thread = threading.Thread(target=self._run_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        with self._lock:
            self._running = False

    def status(self) -> dict:
        with self._lock:
            return {
                "enabled": self._enabled,
                "connected": self._connected,
                "products": list(self._products),
                "last_error": self._last_error,
                "last_message_at": self._last_message_at,
            }

    def symbol_signal(self, symbol: str) -> dict | None:
        product_id = self._symbol_to_product(symbol)
        if not product_id:
            return None

        with self._lock:
            state = self._states.get(product_id)
            if state is None:
                return None
            now = datetime.now(tz=timezone.utc)
            self._prune_old_trades(state, now)
            trade_count = len(state.trades_60s)
            trade_notional = sum(notional for _, notional in state.trades_60s)
            sentiment = max(-1.0, min(state.price_change_pct_24h / 10.0, 1.0))
            momentum = max(0.0, min(trade_count / 40.0, 1.0))
            notional_boost = max(0.0, min(trade_notional / 500000.0, 1.0))
            event_strength = max(abs(sentiment), momentum, notional_boost)
            flags: list[str] = []
            if trade_count >= 20:
                flags.append("WS_TRADE_SURGE")
            if abs(state.price_change_pct_24h) >= 1.5:
                flags.append("WS_PRICE_DISLOCATION")
            if not flags:
                flags.append("WS_NORMAL_FLOW")

            return {
                "product_id": product_id,
                "sentiment_score": round(sentiment, 6),
                "news_momentum_score": round(momentum, 6),
                "event_strength": round(event_strength, 6),
                "event_flags": flags,
                "trades_60s": trade_count,
                "trade_notional_60s": round(trade_notional, 2),
                "last_price": state.last_price,
                "last_update": state.last_update,
            }

    def _symbol_to_product(self, symbol: str) -> str | None:
        upper = symbol.upper()
        if upper.endswith("USD") and len(upper) > 3:
            product = f"{upper[:-3]}-USD"
            return product if product in self._states else None
        return None

    def _run_forever(self) -> None:
        backoff_seconds = 2
        while True:
            with self._lock:
                if not self._running:
                    return

            try:
                self._run_once()
                backoff_seconds = 2
            except Exception as exc:
                with self._lock:
                    self._connected = False
                    self._last_error = str(exc)
                logger.warning("coinbase_ws_loop_error error=%s", exc)
                time.sleep(backoff_seconds)
                backoff_seconds = min(backoff_seconds * 2, 30)

    def _run_once(self) -> None:
        ws = websocket.create_connection(self._url, timeout=10)
        try:
            self._subscribe(ws, channel="heartbeats")
            self._subscribe(ws, channel="ticker")
            self._subscribe(ws, channel="market_trades")
            with self._lock:
                self._connected = True
                self._last_error = None

            while True:
                with self._lock:
                    if not self._running:
                        return
                raw = ws.recv()
                self._handle_message(raw)
        finally:
            with self._lock:
                self._connected = False
            try:
                ws.close()
            except Exception:
                pass

    def _subscribe(self, ws: websocket.WebSocket, *, channel: str) -> None:
        payload = {
            "type": "subscribe",
            "channel": channel,
            "product_ids": list(self._products),
        }
        ws.send(json.dumps(payload))

    def _handle_message(self, raw: str) -> None:
        now = datetime.now(tz=timezone.utc)
        with self._lock:
            self._last_message_at = now

        try:
            payload = json.loads(raw)
        except Exception:
            return

        channel = str(payload.get("channel", "")).lower()
        events = payload.get("events")
        if not isinstance(events, list):
            return

        for event in events:
            if not isinstance(event, dict):
                continue
            if channel == "ticker":
                self._consume_ticker_event(event, now)
            elif channel == "market_trades":
                self._consume_trade_event(event, now)
            elif channel == "heartbeats":
                self._consume_heartbeat(event, now)

    def _consume_heartbeat(self, event: dict, now: datetime) -> None:
        product_id = str(event.get("product_id") or "").upper()
        if not product_id:
            return
        with self._lock:
            state = self._states.get(product_id)
            if state:
                state.last_update = now

    def _consume_ticker_event(self, event: dict, now: datetime) -> None:
        tickers = event.get("tickers")
        if not isinstance(tickers, list):
            return

        with self._lock:
            for ticker in tickers:
                if not isinstance(ticker, dict):
                    continue
                product_id = str(ticker.get("product_id") or "").upper()
                if product_id not in self._states:
                    continue
                state = self._states[product_id]
                state.last_update = now
                state.last_price = self._to_float(ticker.get("price"), state.last_price)
                state.price_change_pct_24h = self._to_float(ticker.get("price_percent_chg_24_h"), state.price_change_pct_24h)
                state.volume_24h = self._to_float(ticker.get("volume_24_h"), state.volume_24h)

    def _consume_trade_event(self, event: dict, now: datetime) -> None:
        trades = event.get("trades")
        if not isinstance(trades, list):
            return

        with self._lock:
            for trade in trades:
                if not isinstance(trade, dict):
                    continue
                product_id = str(trade.get("product_id") or "").upper()
                if product_id not in self._states:
                    continue
                state = self._states[product_id]
                price = self._to_float(trade.get("price"), 0.0)
                size = self._to_float(trade.get("size"), 0.0)
                notional = max(0.0, price * size)
                state.last_update = now
                if price > 0:
                    state.last_price = price
                state.trades_60s.append((now, notional))
                self._prune_old_trades(state, now)

    def _prune_old_trades(self, state: ProductState, now: datetime) -> None:
        cutoff = now.timestamp() - 60.0
        while state.trades_60s and state.trades_60s[0][0].timestamp() < cutoff:
            state.trades_60s.popleft()

    def _to_float(self, value, default: float | None) -> float:
        try:
            return float(value)
        except Exception:
            return float(default or 0.0)


coinbase_ws_service = CoinbaseWsService()
