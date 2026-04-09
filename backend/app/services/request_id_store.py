"""
Thread-safe in-memory store for Alpaca X-Request-ID values.

Alpaca includes a unique X-Request-ID header in every API response.
Persisting recent IDs allows them to be referenced in support requests
to help Alpaca trace calls through their system.
"""
from __future__ import annotations

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.config import settings


@dataclass
class AlpacaRequestIdEntry:
    alpaca_request_id: str
    endpoint: str
    method: str
    status_code: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    symbol: str | None = None


class RequestIdStore:
    """Circular buffer of the most recent Alpaca X-Request-ID values."""

    def __init__(self, maxlen: int | None = None) -> None:
        limit = maxlen if maxlen is not None else settings.request_id_max_entries
        self._entries: deque[AlpacaRequestIdEntry] = deque(maxlen=limit)
        self._lock = threading.Lock()
        self._total: int = 0

    def record(
        self,
        *,
        alpaca_request_id: str,
        endpoint: str,
        method: str,
        status_code: int,
        symbol: str | None = None,
    ) -> None:
        """Store one Alpaca request ID entry. No-op if the ID is empty."""
        if not alpaca_request_id:
            return
        entry = AlpacaRequestIdEntry(
            alpaca_request_id=alpaca_request_id,
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            symbol=symbol,
        )
        with self._lock:
            self._entries.append(entry)
            self._total += 1

    def get_recent(self, n: int = 50) -> list[AlpacaRequestIdEntry]:
        """Return the n most recent entries, newest last."""
        with self._lock:
            return list(self._entries)[-n:]

    @property
    def total_captured(self) -> int:
        with self._lock:
            return self._total

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()
            self._total = 0


request_id_store = RequestIdStore()
