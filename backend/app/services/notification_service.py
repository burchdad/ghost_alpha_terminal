"""
Notification Service
====================
Centralised hub for all operator-facing notifications.

Delivery channels:
  1. In-process SSE event bus  (frontend notification bell, real-time)
  2. Email via SendGrid / SMTP (reuses twofa_service infrastructure)
  3. Discord webhook            (reuses discord_notifier)

Notification events:
  - trade_executed        : a trade was routed to a broker
  - kill_switch_changed   : kill switch enabled or disabled
  - autonomous_cycle      : autonomous runner completed a cycle
  - goal_milestone        : goal target reached / behind pace
  - scan_complete         : opportunity scan finished
  - system_alert          : generic system-level alert
"""
from __future__ import annotations

import asyncio
import json
import logging
import threading
from collections import deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Event model
# ---------------------------------------------------------------------------

@dataclass
class NotificationEvent:
    id: str
    event_type: str          # trade_executed | kill_switch_changed | autonomous_cycle | goal_milestone | scan_complete | system_alert
    title: str
    message: str
    severity: str            # info | success | warning | critical
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(tz=timezone.utc).isoformat())
    read: bool = False

    def to_sse(self) -> str:
        data = json.dumps(asdict(self))
        return f"data: {data}\n\n"


# ---------------------------------------------------------------------------
# SSE subscriber registry
# ---------------------------------------------------------------------------

class _SseRegistry:
    """Holds async queues for each active SSE subscriber."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._queues: list[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        with self._lock:
            self._queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        with self._lock:
            try:
                self._queues.remove(q)
            except ValueError:
                pass

    def broadcast(self, event: NotificationEvent) -> None:
        """Put event into every subscriber queue (non-blocking; drops if full)."""
        with self._lock:
            queues = list(self._queues)
        for q in queues:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                pass


# ---------------------------------------------------------------------------
# Notification Service
# ---------------------------------------------------------------------------

_MAX_HISTORY = 100


class NotificationService:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._history: deque[NotificationEvent] = deque(maxlen=_MAX_HISTORY)
        self._counter = 0
        self._sse = _SseRegistry()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def emit(
        self,
        *,
        event_type: str,
        title: str,
        message: str,
        severity: str = "info",
        payload: dict[str, Any] | None = None,
        send_email: bool = False,
        email_to: str | None = None,
        send_discord: bool = True,
    ) -> NotificationEvent:
        with self._lock:
            self._counter += 1
            event_id = f"notif_{self._counter:06d}"

        event = NotificationEvent(
            id=event_id,
            event_type=event_type,
            title=title,
            message=message,
            severity=severity,
            payload=payload or {},
        )

        with self._lock:
            self._history.append(event)

        # SSE broadcast (non-blocking)
        self._sse.broadcast(event)

        # Discord (background thread to avoid blocking)
        if send_discord:
            threading.Thread(
                target=self._try_discord,
                args=(title, message, severity),
                daemon=True,
            ).start()

        # Email (background thread)
        if send_email and email_to:
            threading.Thread(
                target=self._try_email,
                args=(email_to, title, message),
                daemon=True,
            ).start()

        return event

    def history(self, *, limit: int = 50) -> list[NotificationEvent]:
        with self._lock:
            items = list(self._history)
        return list(reversed(items))[:limit]

    def mark_read(self, event_id: str) -> bool:
        with self._lock:
            for ev in self._history:
                if ev.id == event_id:
                    ev.read = True
                    return True
        return False

    def mark_all_read(self) -> int:
        count = 0
        with self._lock:
            for ev in self._history:
                if not ev.read:
                    ev.read = True
                    count += 1
        return count

    def unread_count(self) -> int:
        with self._lock:
            return sum(1 for ev in self._history if not ev.read)

    def subscribe_sse(self) -> asyncio.Queue:
        return self._sse.subscribe()

    def unsubscribe_sse(self, q: asyncio.Queue) -> None:
        self._sse.unsubscribe(q)

    # ------------------------------------------------------------------
    # Convenience emitters
    # ------------------------------------------------------------------

    def trade_executed(
        self,
        *,
        symbol: str,
        direction: str,
        quantity: float,
        price: float,
        broker: str,
        mode: str,
        email_to: str | None = None,
    ) -> None:
        direction_label = direction.upper()
        self.emit(
            event_type="trade_executed",
            title=f"Trade Executed — {symbol}",
            message=f"{direction_label} {quantity:.4f} {symbol} @ ${price:.2f} via {broker} ({mode})",
            severity="success",
            payload={"symbol": symbol, "direction": direction, "quantity": quantity, "price": price, "broker": broker, "mode": mode},
            send_email=bool(email_to),
            email_to=email_to,
            send_discord=True,
        )

    def kill_switch_changed(self, *, enabled: bool, changed_by: str = "operator") -> None:
        state = "ENABLED (trading halted)" if enabled else "DISABLED (trading resumed)"
        self.emit(
            event_type="kill_switch_changed",
            title=f"Kill Switch {state}",
            message=f"Kill switch was {state} by {changed_by}.",
            severity="critical" if enabled else "warning",
            payload={"kill_switch_enabled": enabled, "changed_by": changed_by},
            send_discord=True,
        )

    def autonomous_cycle_complete(
        self,
        *,
        cycles_run: int,
        trades_attempted: int,
        symbols_scanned: int,
    ) -> None:
        self.emit(
            event_type="autonomous_cycle",
            title="Autonomous Cycle Complete",
            message=f"Cycle #{cycles_run}: scanned {symbols_scanned} symbols, attempted {trades_attempted} trades.",
            severity="info",
            payload={"cycles_run": cycles_run, "trades_attempted": trades_attempted, "symbols_scanned": symbols_scanned},
            send_discord=False,
        )

    def goal_milestone(
        self,
        *,
        milestone: str,
        current_capital: float,
        target_capital: float,
        progress_pct: float,
    ) -> None:
        self.emit(
            event_type="goal_milestone",
            title=f"Goal Milestone — {milestone}",
            message=f"Capital ${current_capital:,.2f} / target ${target_capital:,.2f} ({progress_pct:.1f}%)",
            severity="success" if progress_pct >= 100 else "info",
            payload={"milestone": milestone, "current_capital": current_capital, "target_capital": target_capital, "progress_pct": progress_pct},
            send_discord=True,
        )

    def scan_complete(self, *, symbol_count: int, top_symbol: str | None, top_score: float | None) -> None:
        top_str = f" — top pick: {top_symbol} ({top_score:.2f})" if top_symbol else ""
        self.emit(
            event_type="scan_complete",
            title="Opportunity Scan Complete",
            message=f"Scanned {symbol_count} symbols{top_str}.",
            severity="info",
            payload={"symbol_count": symbol_count, "top_symbol": top_symbol, "top_score": top_score},
            send_discord=False,
        )

    def system_alert(self, *, title: str, message: str, severity: str = "warning") -> None:
        self.emit(
            event_type="system_alert",
            title=title,
            message=message,
            severity=severity,
            send_discord=True,
        )

    # ------------------------------------------------------------------
    # Internal delivery helpers
    # ------------------------------------------------------------------

    def _try_discord(self, title: str, message: str, severity: str) -> None:
        try:
            from app.services.discord_notifier import discord_notifier
            discord_notifier.send_message(
                title=title,
                message=message,
                severity=severity,
            )
        except Exception as exc:
            logger.debug("Discord notification failed (non-critical): %s", exc)

    def _try_email(self, to_email: str, subject: str, body: str) -> None:
        try:
            from app.services.twofa_service import twofa_service
            twofa_service.send_email_code  # existence check
            # Use the SendGrid/SMTP send path directly
            from app.services import twofa_service as _mod
            svc = _mod.twofa_service
            if settings.sendgrid_api_key:
                svc._send_via_sendgrid(to_email=to_email, subject=subject, body=body)
            elif settings.smtp_host:
                svc._send_via_smtp(to_email=to_email, subject=subject, body=body)
        except Exception as exc:
            logger.debug("Email notification failed (non-critical): %s", exc)


notification_service = NotificationService()
