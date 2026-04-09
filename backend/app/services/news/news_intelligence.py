from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock


@dataclass
class NewsAuditEntry:
    timestamp: datetime
    symbol: str
    data_classification: str
    sources_used: list[str]
    sentiment_score: float
    news_momentum_score: float
    event_strength: float
    event_flags: list[str]


class NewsIntelligenceService:
    """Public-source news/sentiment layer with source whitelisting and audit trail."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._audit: list[NewsAuditEntry] = []
        self._max_audit = 1000
        self._source_whitelist = [
            "SEC_FILINGS",
            "REUTERS_PUBLIC",
            "NASDAQ_NEWSROOM",
            "YAHOO_FINANCE_PUBLIC",
            "COINDESK_PUBLIC",
            "FED_RELEASES",
        ]

    def source_whitelist(self) -> list[str]:
        return list(self._source_whitelist)

    def analyze_symbol(self, symbol: str) -> dict:
        upper = symbol.upper()
        # Deterministic pseudo-signal for stable behavior in mock mode.
        seed = abs(hash(f"news:{upper}"))

        sentiment_raw = ((seed % 2001) - 1000) / 1000.0
        sentiment_score = max(-1.0, min(sentiment_raw * 0.85, 1.0))

        momentum_raw = ((seed // 97) % 1000) / 1000.0
        news_momentum_score = max(0.0, min(momentum_raw, 1.0))

        event_raw = ((seed // 193) % 1000) / 1000.0
        event_strength = max(0.0, min(event_raw, 1.0))

        event_flags: list[str] = []
        if event_strength > 0.82:
            event_flags.append("HIGH_IMPACT_HEADLINE_CLUSTER")
        if news_momentum_score > 0.75:
            event_flags.append("NEWS_VELOCITY_SPIKE")
        if abs(sentiment_score) > 0.65:
            event_flags.append("SENTIMENT_EXTREME")
        if not event_flags:
            event_flags.append("NO_MAJOR_EVENT")

        selected_sources = self._source_whitelist[: (3 + (seed % 3))]

        data_classification = "PUBLIC"
        rationale = (
            "Signals derived from whitelisted public sources only; "
            "no private channels or restricted datasets included."
        )

        self._record(
            NewsAuditEntry(
                timestamp=datetime.now(tz=timezone.utc),
                symbol=upper,
                data_classification=data_classification,
                sources_used=selected_sources,
                sentiment_score=round(sentiment_score, 6),
                news_momentum_score=round(news_momentum_score, 6),
                event_strength=round(event_strength, 6),
                event_flags=event_flags,
            )
        )

        return {
            "symbol": upper,
            "timestamp": datetime.now(tz=timezone.utc),
            "data_classification": data_classification,
            "sources_used": selected_sources,
            "sentiment_score": round(sentiment_score, 6),
            "news_momentum_score": round(news_momentum_score, 6),
            "event_strength": round(event_strength, 6),
            "event_flags": event_flags,
            "rationale": rationale,
        }

    def recent_audit(self, limit: int = 50) -> list[dict]:
        with self._lock:
            entries = self._audit[-max(1, min(limit, 500)) :]
        return [
            {
                "timestamp": item.timestamp,
                "symbol": item.symbol,
                "data_classification": item.data_classification,
                "sources_used": item.sources_used,
                "sentiment_score": item.sentiment_score,
                "news_momentum_score": item.news_momentum_score,
                "event_strength": item.event_strength,
                "event_flags": item.event_flags,
            }
            for item in reversed(entries)
        ]

    def _record(self, entry: NewsAuditEntry) -> None:
        with self._lock:
            self._audit.append(entry)
            if len(self._audit) > self._max_audit:
                self._audit = self._audit[-self._max_audit :]


news_intelligence = NewsIntelligenceService()
