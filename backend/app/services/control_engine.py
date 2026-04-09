from __future__ import annotations

import logging
from datetime import datetime, timezone
from threading import Lock

from app.services.kill_switch import kill_switch
from app.services.trade_guardrails import trade_guardrails

logger = logging.getLogger(__name__)


class ControlEngine:
    def __init__(self) -> None:
        self._lock = Lock()
        self._starting_balance = 100000.0
        self._equity = 100000.0
        self._peak_equity = 100000.0
        self._daily_pnl = 0.0
        self._daily_loss = 0.0
        self._current_day = datetime.now(tz=timezone.utc).date()
        self._reject_log: list[dict] = []
        self._safe_mode = True
        self._daily_loss_limit_pct: float = 0.05
        self._max_drawdown_limit_pct: float = 0.10

    def _rollover_day_if_needed(self) -> None:
        today = datetime.now(tz=timezone.utc).date()
        if today != self._current_day:
            self._current_day = today
            self._daily_pnl = 0.0
            self._daily_loss = 0.0

    def _log_reject(self, reason: str, symbol: str) -> None:
        event = {
            "timestamp": datetime.now(tz=timezone.utc),
            "symbol": symbol.upper(),
            "reason": reason,
        }
        logger.warning("trade_rejected symbol=%s reason=%s", symbol.upper(), reason)
        self._reject_log.append(event)
        if len(self._reject_log) > 200:
            self._reject_log = self._reject_log[-200:]

    def set_limits(
        self,
        *,
        daily_loss_limit_pct: float | None = None,
        max_drawdown_limit_pct: float | None = None,
    ) -> dict:
        with self._lock:
            if daily_loss_limit_pct is not None:
                self._daily_loss_limit_pct = max(0.001, min(0.5, daily_loss_limit_pct))
            if max_drawdown_limit_pct is not None:
                self._max_drawdown_limit_pct = max(0.001, min(0.5, max_drawdown_limit_pct))
            return {
                "daily_loss_limit_pct": self._daily_loss_limit_pct,
                "max_drawdown_limit_pct": self._max_drawdown_limit_pct,
                "daily_loss_limit": round(self._starting_balance * self._daily_loss_limit_pct, 2),
            }

    def _limits_breached(self) -> tuple[bool, str]:
        daily_loss_limit = self._starting_balance * self._daily_loss_limit_pct
        if self._daily_loss > daily_loss_limit:
            return True, f"Daily loss limit exceeded ({self._daily_loss_limit_pct*100:.1f}%): trading paused."

        drawdown = max(0.0, self._peak_equity - self._equity)
        if drawdown > self._peak_equity * self._max_drawdown_limit_pct:
            return True, f"Max drawdown exceeded ({self._max_drawdown_limit_pct*100:.1f}%): trading paused."

        return False, ""

    def update_balance(self, *, pnl: float) -> None:
        with self._lock:
            self._rollover_day_if_needed()
            self._daily_pnl += pnl
            if pnl < 0:
                self._daily_loss += abs(pnl)
            self._equity += pnl
            self._peak_equity = max(self._peak_equity, self._equity)

            breached, _ = self._limits_breached()
            if breached:
                kill_switch.set_enabled(False)

    def validate_trade(
        self,
        *,
        symbol: str,
        confidence: float,
        expected_value: float,
        risk_reward_ratio: float,
        position_size: float,
        position_notional: float,
        account_balance: float,
    ) -> tuple[bool, str]:
        with self._lock:
            self._rollover_day_if_needed()

            if not kill_switch.is_enabled():
                reason = "Execution blocked: kill switch is OFF."
                self._log_reject(reason, symbol)
                return False, reason

            breached, reason = self._limits_breached()
            if breached:
                self._log_reject(reason, symbol)
                kill_switch.set_enabled(False)
                return False, reason

            ok, reason = trade_guardrails.validate(
                confidence=confidence,
                expected_value=expected_value,
                risk_reward_ratio=risk_reward_ratio,
                position_size=position_size,
                position_notional=position_notional,
                account_balance=account_balance,
            )
            if not ok:
                self._log_reject(reason, symbol)
                return False, reason

            return True, ""

    def set_kill_switch(self, enabled: bool) -> bool:
        return kill_switch.set_enabled(enabled)

    def status(self) -> dict:
        with self._lock:
            self._rollover_day_if_needed()
            drawdown = max(0.0, self._peak_equity - self._equity)
            drawdown_pct = drawdown / self._peak_equity if self._peak_equity > 0 else 0.0
            return {
                "trading_enabled": kill_switch.is_enabled(),
                "system_status": "ACTIVE" if kill_switch.is_enabled() else "PAUSED",
                "mode": "SAFE" if self._safe_mode else "NORMAL",
                "daily_pnl": round(self._daily_pnl, 2),
                "daily_loss": round(self._daily_loss, 2),
                "daily_loss_limit": round(self._starting_balance * self._daily_loss_limit_pct, 2),
                "daily_loss_limit_pct": self._daily_loss_limit_pct,
                "rolling_drawdown": round(drawdown, 2),
                "rolling_drawdown_pct": round(drawdown_pct, 4),
                "max_drawdown_limit_pct": self._max_drawdown_limit_pct,
                "rejected_trades": [
                    {
                        "timestamp": item["timestamp"],
                        "symbol": item["symbol"],
                        "reason": item["reason"],
                    }
                    for item in self._reject_log[-20:]
                ],
            }


control_engine = ControlEngine()
