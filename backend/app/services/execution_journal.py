from __future__ import annotations

import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ExecutionJournalEntry:
    execution_id: str
    cycle_id: str
    symbol: str
    regime: str
    action: str
    strategy: str
    confidence: float
    risk_level: str
    allocation_pct: float
    qty: float
    notional: float
    mode: str
    submitted: bool
    order_id: str | None
    reason: str
    error: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    outcome_label: str | None = None
    pnl: float | None = None


class ExecutionJournal:
    def __init__(self, maxlen: int = 500) -> None:
        self._entries: deque[ExecutionJournalEntry] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, **kwargs) -> ExecutionJournalEntry:
        entry = ExecutionJournalEntry(execution_id=uuid.uuid4().hex, **kwargs)
        with self._lock:
            self._entries.append(entry)
        return entry

    def recent(self, limit: int = 50) -> list[ExecutionJournalEntry]:
        with self._lock:
            return list(self._entries)[-limit:]

    def update_outcome(self, cycle_id: str, *, outcome_label: str, pnl: float) -> None:
        with self._lock:
            for entry in reversed(self._entries):
                if entry.cycle_id == cycle_id:
                    entry.outcome_label = outcome_label
                    entry.pnl = pnl
                    break


execution_journal = ExecutionJournal()