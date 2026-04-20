"""
Tradier Order Sync Service
==========================
Polls Tradier every POLL_INTERVAL_SECONDS for live orders and positions,
tracks status transitions, and exposes a snapshot for the execution
confirmation layer and portfolio routes.

Status lifecycle tracked per order:
  submitted → pending / partially_filled → filled / canceled / rejected

The service stores only the last MAX_ORDERS_RETAINED orders so memory usage
stays bounded across long trading sessions.
"""
from __future__ import annotations

import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger(__name__)

POLL_INTERVAL_SECONDS = 2
MAX_ORDERS_RETAINED = 500

TradierOrderStatus = Literal[
    "open",
    "partially_filled",
    "filled",
    "expired",
    "canceled",
    "pending",
    "rejected",
    "error",
]


@dataclass
class TradierOrderState:
    order_id: str
    symbol: str
    side: str
    qty: float
    order_type: str
    status: TradierOrderStatus
    avg_fill_price: float | None
    exec_quantity: float
    remaining_quantity: float
    created_at: str | None
    updated_at: str | None
    raw: dict = field(default_factory=dict)
    # Transition log: list of (status, timestamp)
    transitions: list[tuple[str, datetime]] = field(default_factory=list)

    def record_transition(self, new_status: str) -> None:
        self.transitions.append((new_status, datetime.now(tz=timezone.utc)))

    def to_dict(self) -> dict:
        return {
            "order_id": self.order_id,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "order_type": self.order_type,
            "status": self.status,
            "avg_fill_price": self.avg_fill_price,
            "exec_quantity": self.exec_quantity,
            "remaining_quantity": self.remaining_quantity,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "transitions": [
                {"status": s, "at": t.isoformat()} for s, t in self.transitions
            ],
        }


class TradierOrderSyncService:
    """Background thread that keeps Tradier order and position state up-to-date."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._running = False

        # order_id -> TradierOrderState
        self._orders: dict[str, TradierOrderState] = {}
        self._order_history: deque[TradierOrderState] = deque(maxlen=MAX_ORDERS_RETAINED)

        # Live positions from Tradier
        self._positions: list[dict] = []

        # Last successful sync timestamps
        self._last_orders_sync: datetime | None = None
        self._last_positions_sync: datetime | None = None
        self._last_error: str | None = None
        self._sync_count: int = 0

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        with self._lock:
            if self._running:
                return
            self._stop_event.clear()
            self._thread = threading.Thread(
                target=self._loop,
                name="tradier-order-sync",
                daemon=True,
            )
            self._running = True
            self._thread.start()
        logger.info("TradierOrderSyncService started (poll interval: %ds)", POLL_INTERVAL_SECONDS)

    def stop(self) -> None:
        self._stop_event.set()
        with self._lock:
            self._running = False
        logger.info("TradierOrderSyncService stopping.")

    # ------------------------------------------------------------------
    # Public snapshot API
    # ------------------------------------------------------------------

    def open_orders(self) -> list[dict]:
        """Return all currently open/pending orders as dicts."""
        with self._lock:
            return [
                v.to_dict()
                for v in self._orders.values()
                if v.status in {"open", "partially_filled", "pending"}
            ]

    def all_orders(self) -> list[dict]:
        """Return all tracked orders (open + recent history)."""
        with self._lock:
            live = [v.to_dict() for v in self._orders.values()]
            hist = [v.to_dict() for v in self._order_history]
            # Deduplicate: live takes precedence
            live_ids = {v["order_id"] for v in live}
            return live + [h for h in hist if h["order_id"] not in live_ids]

    def get_order(self, order_id: str) -> dict | None:
        """Return a single order by ID or None."""
        with self._lock:
            if order_id in self._orders:
                return self._orders[order_id].to_dict()
            for entry in self._order_history:
                if entry.order_id == order_id:
                    return entry.to_dict()
        return None

    def positions(self) -> list[dict]:
        """Return the latest positions snapshot from Tradier."""
        with self._lock:
            return list(self._positions)

    def health(self) -> dict:
        with self._lock:
            return {
                "running": self._running,
                "sync_count": self._sync_count,
                "open_order_count": len([v for v in self._orders.values() if v.status in {"open", "partially_filled", "pending"}]),
                "position_count": len(self._positions),
                "last_orders_sync": self._last_orders_sync.isoformat() if self._last_orders_sync else None,
                "last_positions_sync": self._last_positions_sync.isoformat() if self._last_positions_sync else None,
                "last_error": self._last_error,
            }

    # ------------------------------------------------------------------
    # Manual force-fetch (for confirmation endpoints)
    # ------------------------------------------------------------------

    def force_refresh(self) -> dict:
        """Synchronously run one poll cycle and return the health dict."""
        self._poll_orders()
        self._poll_positions()
        return self.health()

    # ------------------------------------------------------------------
    # Internal loop
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._poll_orders()
                self._poll_positions()
                with self._lock:
                    self._sync_count += 1
            except Exception as exc:
                with self._lock:
                    self._last_error = str(exc)
                logger.warning("TradierOrderSyncService poll error: %s", exc)
            self._stop_event.wait(POLL_INTERVAL_SECONDS)

    def _poll_orders(self) -> None:
        from app.core.config import settings
        from app.services.tradier_client import tradier_client

        if not tradier_client.is_configured():
            return

        try:
            payload = tradier_client.get(
                f"/accounts/{settings.tradier_effective_account_number}/orders",
                params={"includeTags": "true"},
            )
        except Exception as exc:
            with self._lock:
                self._last_error = f"orders poll: {exc}"
            return

        orders_block = (payload or {}).get("orders", {})
        if not orders_block or orders_block == "null":
            with self._lock:
                self._last_orders_sync = datetime.now(tz=timezone.utc)
            return

        raw_orders = orders_block.get("order", [])
        if isinstance(raw_orders, dict):
            raw_orders = [raw_orders]
        if not isinstance(raw_orders, list):
            return

        now = datetime.now(tz=timezone.utc)
        with self._lock:
            seen_ids: set[str] = set()
            for raw in raw_orders:
                if not isinstance(raw, dict):
                    continue
                oid = str(raw.get("id", ""))
                if not oid:
                    continue
                seen_ids.add(oid)
                new_status: TradierOrderStatus = raw.get("status", "open")
                if oid in self._orders:
                    existing = self._orders[oid]
                    if existing.status != new_status:
                        existing.record_transition(new_status)
                        existing.status = new_status
                        existing.avg_fill_price = float(raw.get("avg_fill_price") or 0.0) or None
                        existing.exec_quantity = float(raw.get("exec_quantity") or 0.0)
                        existing.remaining_quantity = float(raw.get("remaining_quantity") or 0.0)
                        existing.updated_at = now.isoformat()
                        existing.raw = raw
                        # Move terminal orders to history
                        if new_status in {"filled", "canceled", "rejected", "expired", "error"}:
                            self._order_history.append(existing)
                            del self._orders[oid]
                else:
                    state = TradierOrderState(
                        order_id=oid,
                        symbol=str(raw.get("symbol", "")),
                        side=str(raw.get("side", "")),
                        qty=float(raw.get("quantity") or 0.0),
                        order_type=str(raw.get("type", "")),
                        status=new_status,
                        avg_fill_price=float(raw.get("avg_fill_price") or 0.0) or None,
                        exec_quantity=float(raw.get("exec_quantity") or 0.0),
                        remaining_quantity=float(raw.get("remaining_quantity") or 0.0),
                        created_at=str(raw.get("create_date", "")),
                        updated_at=now.isoformat(),
                        raw=raw,
                        transitions=[(new_status, now)],
                    )
                    if new_status in {"filled", "canceled", "rejected", "expired", "error"}:
                        self._order_history.append(state)
                    else:
                        self._orders[oid] = state

            self._last_orders_sync = now

    def _poll_positions(self) -> None:
        from app.core.config import settings
        from app.services.tradier_client import tradier_client

        if not tradier_client.is_configured():
            return

        try:
            payload = tradier_client.get(
                f"/accounts/{settings.tradier_effective_account_number}/positions"
            )
        except Exception as exc:
            with self._lock:
                self._last_error = f"positions poll: {exc}"
            return

        positions_block = (payload or {}).get("positions", {})
        if not positions_block or positions_block == "null":
            with self._lock:
                self._positions = []
                self._last_positions_sync = datetime.now(tz=timezone.utc)
            return

        raw_positions = positions_block.get("position", [])
        if isinstance(raw_positions, dict):
            raw_positions = [raw_positions]
        if not isinstance(raw_positions, list):
            raw_positions = []

        with self._lock:
            self._positions = raw_positions
            self._last_positions_sync = datetime.now(tz=timezone.utc)


tradier_order_sync_service = TradierOrderSyncService()
