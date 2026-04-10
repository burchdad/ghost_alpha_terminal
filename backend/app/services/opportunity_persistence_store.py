from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock


@dataclass
class PersistenceRow:
    ts: datetime
    score: float
    confidence: float
    regime: str
    news_strength: float
    volume_spike: float


class OpportunityPersistenceStore:
    """Short-horizon persistence memory so durable setups outrank one-cycle flashes."""

    def __init__(self, max_rows_per_symbol: int = 20) -> None:
        self._lock = Lock()
        self._rows: dict[str, deque[PersistenceRow]] = defaultdict(lambda: deque(maxlen=max_rows_per_symbol))

    def score(
        self,
        *,
        symbol: str,
        score: float,
        confidence: float,
        regime: str,
        news_strength: float,
        volume_spike: float,
    ) -> dict:
        now = datetime.now(tz=timezone.utc)
        key = symbol.upper()
        with self._lock:
            hist = list(self._rows.get(key, deque()))

        recent = [r for r in hist if (now - r.ts) <= timedelta(hours=12)]
        if not recent:
            return {
                "persistence_bonus": 0.0,
                "trend_bonus": 0.0,
                "alignment_bonus": 0.0,
                "total_bonus": 0.0,
                "observations": 0,
            }

        persistence_bonus = min(len(recent) / 6.0, 1.0) * 0.08

        half = max(len(recent) // 2, 1)
        older = recent[:half]
        newer = recent[half:]
        older_avg = sum(r.score for r in older) / max(len(older), 1)
        newer_avg = sum(r.score for r in newer) / max(len(newer), 1)
        trend_bonus = max(-0.03, min((newer_avg - older_avg) * 0.20, 0.05))

        same_regime = sum(1 for r in recent if r.regime == regime)
        regime_alignment = same_regime / max(len(recent), 1)
        news_alignment = 1.0 - min(abs((sum(r.news_strength for r in recent) / len(recent)) - news_strength), 1.0)
        alignment_bonus = max(0.0, min((regime_alignment * 0.6 + news_alignment * 0.4 - 0.5) * 0.08, 0.05))

        total_bonus = max(-0.04, min(persistence_bonus + trend_bonus + alignment_bonus, 0.14))
        return {
            "persistence_bonus": round(persistence_bonus, 4),
            "trend_bonus": round(trend_bonus, 4),
            "alignment_bonus": round(alignment_bonus, 4),
            "total_bonus": round(total_bonus, 4),
            "observations": len(recent),
        }

    def record_batch(self, items: list[dict]) -> None:
        now = datetime.now(tz=timezone.utc)
        with self._lock:
            for item in items:
                symbol = str(item.get("symbol", "")).upper().strip()
                if not symbol:
                    continue
                self._rows[symbol].append(
                    PersistenceRow(
                        ts=now,
                        score=float(item.get("opportunity_score", 0.0) or 0.0),
                        confidence=float(item.get("consensus_confidence", 0.0) or 0.0),
                        regime=str(item.get("regime", "UNKNOWN")),
                        news_strength=float(item.get("event_strength", 0.0) or 0.0),
                        volume_spike=float(item.get("avg_dollar_volume", 0.0) or 0.0),
                    )
                )


opportunity_persistence_store = OpportunityPersistenceStore()
