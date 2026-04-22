"""
Execution Bridge — connects swarm consensus to routed broker execution.

Responsibilities:
  - Gate on the existing control_engine kill switch + guardrails
    - Convert swarm action (BUY/SELL/HOLD) into a broker-routed market order
  - Return a dict capturing the result (order ID, error, or skipped)
    - Enforce broker-specific mode and configuration guards
"""
from __future__ import annotations

import logging
from typing import Literal

from app.core.config import settings
from app.services.brokers.base import BrokerOrderRequest
from app.services.brokers.router import broker_router
from app.services.execution_policy_service import execution_policy_service
from app.services.explainability import build_explainability
from app.services.kill_switch import kill_switch

logger = logging.getLogger(__name__)

ExecutionMode = Literal["SIMULATION", "PAPER_TRADING", "LIVE_TRADING"]


class ExecutionBridge:
    """Translates swarm BUY/SELL/HOLD into routed broker orders."""

    def __init__(self) -> None:
        self._mode: ExecutionMode = "SIMULATION"

    def set_mode(self, mode: ExecutionMode) -> ExecutionMode:
        self._mode = mode
        return self._mode

    def get_mode(self) -> ExecutionMode:
        return self._mode

    def broker_capabilities(self) -> dict[str, dict]:
        return broker_router.capabilities_map()

    def submit(
        self,
        *,
        symbol: str,
        action: Literal["BUY", "SELL", "HOLD"],
        qty: float,
        confidence: float,
        user_id: str | None = None,
        client_order_id: str | None = None,
        liquidity_score: float = 1.0,
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
            "broker": None,
            "explainability": None,
        }

        if self._mode == "SIMULATION":
            return {
                **base,
                "track_position": action != "HOLD",
                "reason": "Execution mode is SIMULATION — decision logged only.",
                "explainability": build_explainability(
                    reasoning="Insight-only mode is active; order not sent to broker.",
                    confidence=confidence,
                    risk_level="N/A",
                    expected_value=0.0,
                    accepted=action != "HOLD",
                    safeguards=["human_in_the_loop_default", "execution_mode_simulation"],
                    inputs={"symbol": symbol, "action": action, "qty": qty},
                ),
            }

        # Gate 1 — HOLD: nothing to do
        if action == "HOLD":
            return {
                **base,
                "reason": "Action is HOLD — no order placed.",
                "explainability": build_explainability(
                    reasoning="No directional edge; execution intentionally skipped.",
                    confidence=confidence,
                    risk_level="LOW",
                    expected_value=0.0,
                    accepted=False,
                    safeguards=["hold_gate"],
                    inputs={"symbol": symbol, "action": action},
                ),
            }

        # Gate 2 — kill switch
        if not kill_switch.is_enabled():
            return {
                **base,
                "reason": "Kill switch is active — trading disabled.",
                "explainability": build_explainability(
                    reasoning="Global risk stop blocked execution.",
                    confidence=confidence,
                    risk_level="HIGH",
                    expected_value=0.0,
                    accepted=False,
                    safeguards=["kill_switch"],
                    inputs={"symbol": symbol, "action": action},
                ),
            }

        routed_broker = broker_router.route_broker(
            symbol=symbol,
            liquidity_score=liquidity_score,
            mode=self._mode,
            user_id=user_id,
        )

        # Gate 3 — credentials not configured for Alpaca routes
        if routed_broker == "alpaca" and (not settings.alpaca_api_key or not settings.alpaca_secret_key):
            return {
                **base,
                "reason": (
                    "Alpaca credentials not configured. "
                    "Set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env to enable execution."
                ),
                "explainability": build_explainability(
                    reasoning="Execution blocked because broker credentials are unavailable.",
                    confidence=confidence,
                    risk_level="MEDIUM",
                    expected_value=0.0,
                    accepted=False,
                    safeguards=["credential_gate"],
                    inputs={"symbol": symbol, "action": action},
                ),
            }

        # Map side and enforce mode-broker consistency checks
        side = "buy" if action == "BUY" else "sell"
        if routed_broker == "alpaca" and self._mode == "LIVE_TRADING" and settings.alpaca_paper:
            return {
                **base,
                "reason": "LIVE_TRADING selected but ALPACA_PAPER=true. Disable paper mode to place live orders.",
                "explainability": build_explainability(
                    reasoning="Environment is paper-configured; live orders are blocked by policy.",
                    confidence=confidence,
                    risk_level="HIGH",
                    expected_value=0.0,
                    accepted=False,
                    safeguards=["mode_config_guard"],
                    inputs={"symbol": symbol, "mode": self._mode},
                ),
            }

        if routed_broker == "alpaca" and self._mode == "PAPER_TRADING" and not settings.alpaca_paper:
            return {
                **base,
                "reason": "PAPER_TRADING selected but ALPACA_PAPER=false. Enable paper mode before trading.",
                "explainability": build_explainability(
                    reasoning="Paper mode requested while broker is configured for live endpoint.",
                    confidence=confidence,
                    risk_level="HIGH",
                    expected_value=0.0,
                    accepted=False,
                    safeguards=["mode_config_guard"],
                    inputs={"symbol": symbol, "mode": self._mode},
                ),
            }

        if routed_broker == "coinbase" and self._mode != "LIVE_TRADING":
            return {
                **base,
                "reason": "Coinbase execution requires LIVE_TRADING mode.",
                "explainability": build_explainability(
                    reasoning="Coinbase routes are blocked outside live mode to avoid ambiguous paper behavior.",
                    confidence=confidence,
                    risk_level="HIGH",
                    expected_value=0.0,
                    accepted=False,
                    safeguards=["mode_config_guard"],
                    inputs={"symbol": symbol, "mode": self._mode, "broker": routed_broker},
                ),
            }

        if routed_broker == "tradier" and self._mode != "LIVE_TRADING":
            return {
                **base,
                "reason": "Tradier execution requires LIVE_TRADING mode.",
                "explainability": build_explainability(
                    reasoning="Tradier routes are blocked outside live mode.",
                    confidence=confidence,
                    risk_level="HIGH",
                    expected_value=0.0,
                    accepted=False,
                    safeguards=["mode_config_guard"],
                    inputs={"symbol": symbol, "mode": self._mode, "broker": routed_broker},
                ),
            }

        if self._mode == "LIVE_TRADING":
            allowed, reason = execution_policy_service.is_live_execution_allowed_now()
            if not allowed:
                return {
                    **base,
                    "reason": reason or "Live execution blocked by execution policy.",
                    "explainability": build_explainability(
                        reasoning=reason or "Execution policy blocks live orders at this time.",
                        confidence=confidence,
                        risk_level="HIGH",
                        expected_value=0.0,
                        accepted=False,
                        safeguards=["execution_policy_guard"],
                        inputs={"symbol": symbol, "mode": self._mode, "broker": routed_broker},
                    ),
                }

        broker_result = broker_router.submit(
            request=BrokerOrderRequest(
                symbol=symbol,
                side=side,
                qty=max(qty, 0.0001),
                user_id=user_id,
                order_type="market",
                time_in_force="day",
                client_order_id=client_order_id,
            ),
            liquidity_score=liquidity_score,
            mode=self._mode,
        )

        logger.info(
            "broker_order_result symbol=%s broker=%s submitted=%s reason=%s",
            symbol,
            broker_result.broker,
            broker_result.submitted,
            broker_result.reason,
        )
        return {
            **base,
            "submitted": broker_result.submitted,
            "track_position": broker_result.submitted,
            "broker": broker_result.broker,
            "order_id": broker_result.order_id,
            "error": broker_result.error,
            "reason": broker_result.reason,
            "explainability": build_explainability(
                reasoning=broker_result.reason,
                confidence=confidence,
                risk_level="MEDIUM",
                expected_value=0.0,
                accepted=broker_result.submitted,
                safeguards=["broker_router", "kill_switch", "mode_guard"],
                inputs={"symbol": symbol, "action": action, "qty": qty, "broker": broker_result.broker},
            ),
        }


execution_bridge = ExecutionBridge()
