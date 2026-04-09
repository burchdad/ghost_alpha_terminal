"""
Execution Bridge — connects the swarm consensus to Alpaca paper trading.

Responsibilities:
  - Gate on the existing control_engine kill switch + guardrails
  - Convert swarm action (BUY/SELL/HOLD) into an Alpaca market order
  - Return a dict capturing the result (order ID, error, or skipped)
  - All trades are paper-only until credentials are populated in config

Alpaca market order endpoint:
  POST /v2/orders
  {symbol, qty, side, type, time_in_force}
"""
from __future__ import annotations

import logging
from typing import Literal

import httpx

from app.core.config import settings
from app.services.alpaca_client import alpaca_client
from app.services.kill_switch import kill_switch

logger = logging.getLogger(__name__)

ExecutionMode = Literal["SIMULATION", "PAPER_TRADING", "LIVE_TRADING"]


class ExecutionBridge:
    """Translates swarm BUY/SELL/HOLD into Alpaca paper orders."""

    def __init__(self) -> None:
        self._mode: ExecutionMode = "SIMULATION"

    def set_mode(self, mode: ExecutionMode) -> ExecutionMode:
        self._mode = mode
        return self._mode

    def get_mode(self) -> ExecutionMode:
        return self._mode

    def submit(
        self,
        *,
        symbol: str,
        action: Literal["BUY", "SELL", "HOLD"],
        qty: float,
        confidence: float,
        client_order_id: str | None = None,
    ) -> dict:
        """
        Submit to Alpaca if all gates pass.

        Returns a result dict with keys:
          submitted   bool
          action      "BUY" | "SELL" | "HOLD"
          reason      str (why blocked, or order summary)
          order_id    str | None
          error       str | None
        """
        base: dict = {
            "submitted": False,
            "action": action,
            "order_id": None,
            "error": None,
            "mode": self._mode,
            "track_position": False,
        }

        if self._mode == "SIMULATION":
            return {
                **base,
                "track_position": action != "HOLD",
                "reason": "Execution mode is SIMULATION — decision logged only.",
            }

        # Gate 1 — HOLD: nothing to do
        if action == "HOLD":
            return {**base, "reason": "Action is HOLD — no order placed."}

        # Gate 2 — kill switch
        if not kill_switch.is_enabled():
            return {**base, "reason": "Kill switch is active — trading disabled."}

        # Gate 3 — credentials not configured (dev/paper mode without keys)
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            return {
                **base,
                "reason": (
                    "Alpaca credentials not configured. "
                    "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env to enable execution."
                ),
            }

        # Map to Alpaca side
        side = "buy" if action == "BUY" else "sell"
        if self._mode == "LIVE_TRADING" and settings.alpaca_paper:
            return {
                **base,
                "reason": "LIVE_TRADING selected but ALPACA_PAPER=true. Disable paper mode to place live orders.",
            }

        if self._mode == "PAPER_TRADING" and not settings.alpaca_paper:
            return {
                **base,
                "reason": "PAPER_TRADING selected but ALPACA_PAPER=false. Enable paper mode before trading.",
            }

        order_payload = {
            "symbol": symbol,
            "qty": str(qty),
            "side": side,
            "type": "market",
            "time_in_force": "day",
        }
        if client_order_id:
            order_payload["client_order_id"] = client_order_id

        try:
            response = alpaca_client.post(
                "/v2/orders",
                body=order_payload,
                symbol=symbol,
            )
            order_id = response.get("id", "")
            logger.info(
                "alpaca_order_submitted symbol=%s side=%s qty=%s order_id=%s",
                symbol,
                side,
                qty,
                order_id,
            )
            return {
                **base,
                "submitted": True,
                "track_position": True,
                "order_id": order_id,
                "reason": f"Order submitted: {side.upper()} {qty} {symbol} @ market.",
            }

        except httpx.HTTPStatusError as exc:
            err = f"Alpaca HTTP {exc.response.status_code}: {exc.response.text[:200]}"
            logger.error("alpaca_order_failed symbol=%s error=%s", symbol, err)
            return {**base, "error": err, "reason": "Alpaca rejected the order."}

        except httpx.RequestError as exc:
            err = f"Network error: {exc}"
            logger.error("alpaca_order_network_error symbol=%s error=%s", symbol, err)
            return {**base, "error": err, "reason": "Network error reaching Alpaca."}


execution_bridge = ExecutionBridge()
