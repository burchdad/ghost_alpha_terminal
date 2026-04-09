from __future__ import annotations

import logging
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


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
        self._db_loaded = False

    def _ensure_loaded(self) -> None:
        """Lazy-load persisted entries from DB on first access."""
        if self._db_loaded:
            return
        self._db_loaded = True
        try:
            from app.db.models import ExecutionJournalDB
            from app.db.session import get_session

            with get_session() as session:
                rows = (
                    session.query(ExecutionJournalDB)
                    .order_by(ExecutionJournalDB.timestamp.asc())
                    .limit(self._entries.maxlen or 500)
                    .all()
                )
                loaded = 0
                for row in rows:
                    entry = ExecutionJournalEntry(
                        execution_id=row.execution_id,
                        cycle_id=row.cycle_id,
                        symbol=row.symbol,
                        regime=row.regime,
                        action=row.action,
                        strategy=row.strategy,
                        confidence=row.confidence,
                        risk_level=row.risk_level,
                        allocation_pct=row.allocation_pct,
                        qty=row.qty,
                        notional=row.notional,
                        mode=row.mode,
                        submitted=row.submitted,
                        order_id=row.order_id,
                        reason=row.reason or "",
                        error=row.error,
                        timestamp=row.timestamp,
                        outcome_label=row.outcome_label,
                        pnl=row.pnl,
                    )
                    self._entries.append(entry)
                    loaded += 1
                if loaded:
                    logger.info("execution_journal loaded %d entries from DB", loaded)
        except Exception as exc:  # noqa: BLE001
            logger.warning("execution_journal DB load failed: %s", exc)

    def _save_to_db(self, entry: ExecutionJournalEntry) -> None:
        try:
            from app.db.models import ExecutionJournalDB
            from app.db.session import get_session

            with get_session() as session:
                session.add(
                    ExecutionJournalDB(
                        execution_id=entry.execution_id,
                        cycle_id=entry.cycle_id,
                        symbol=entry.symbol,
                        regime=entry.regime,
                        action=entry.action,
                        strategy=entry.strategy,
                        confidence=entry.confidence,
                        risk_level=entry.risk_level,
                        allocation_pct=entry.allocation_pct,
                        qty=entry.qty,
                        notional=entry.notional,
                        mode=entry.mode,
                        submitted=entry.submitted,
                        order_id=entry.order_id,
                        reason=entry.reason or "",
                        error=entry.error,
                        timestamp=entry.timestamp,
                        outcome_label=entry.outcome_label,
                        pnl=entry.pnl,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("execution_journal DB save failed: %s", exc)

    def _update_db_outcome(self, cycle_id: str, *, outcome_label: str, pnl: float) -> None:
        try:
            from app.db.models import ExecutionJournalDB
            from app.db.session import get_session

            with get_session() as session:
                row = (
                    session.query(ExecutionJournalDB)
                    .filter(ExecutionJournalDB.cycle_id == cycle_id)
                    .order_by(ExecutionJournalDB.timestamp.desc())
                    .first()
                )
                if row:
                    row.outcome_label = outcome_label
                    row.pnl = pnl
        except Exception as exc:  # noqa: BLE001
            logger.warning("execution_journal DB outcome update failed: %s", exc)

    def append(self, **kwargs) -> ExecutionJournalEntry:
        entry = ExecutionJournalEntry(execution_id=uuid.uuid4().hex, **kwargs)
        with self._lock:
            self._db_loaded = True  # mark loaded so _ensure_loaded is skipped on next recent()
            self._entries.append(entry)
        self._save_to_db(entry)
        return entry

    def recent(self, limit: int = 50) -> list[ExecutionJournalEntry]:
        with self._lock:
            if not self._db_loaded:
                pass  # release lock before IO
            else:
                return list(self._entries)[-limit:]
        self._ensure_loaded()
        with self._lock:
            return list(self._entries)[-limit:]

    def update_outcome(self, cycle_id: str, *, outcome_label: str, pnl: float) -> None:
        with self._lock:
            for entry in reversed(self._entries):
                if entry.cycle_id == cycle_id:
                    entry.outcome_label = outcome_label
                    entry.pnl = pnl
                    break
        self._update_db_outcome(cycle_id, outcome_label=outcome_label, pnl=pnl)


execution_journal = ExecutionJournal()