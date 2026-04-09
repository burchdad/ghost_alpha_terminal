from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock

from app.services.alpaca_client import alpaca_client
from app.services.news.coinbase_ws_service import coinbase_ws_service


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
        selected_sources = ["ALPACA_NEWS"]
        articles = alpaca_client.get_news(symbol=upper, limit=10)
        sentiment_score = 0.0
        news_momentum_score = 0.0
        event_strength = 0.0
        event_flags: list[str] = []

        if articles:
            article_scores = [self._score_article(article) for article in articles]
            sentiment_score = sum(score for score, _ in article_scores) / len(article_scores)
            news_momentum_score = min(1.0, len(articles) / 10.0)
            event_strength = max(abs(sentiment_score), news_momentum_score)
            if len(articles) >= 6:
                event_flags.append("HEADLINE_CLUSTER")
            if news_momentum_score >= 0.7:
                event_flags.append("NEWS_VELOCITY_SPIKE")
            if abs(sentiment_score) >= 0.45:
                event_flags.append("SENTIMENT_EXTREME")
            for _, article_flag in article_scores:
                if article_flag and article_flag not in event_flags:
                    event_flags.append(article_flag)
        else:
            event_flags.append("NO_RECENT_ALPACA_NEWS")

        ws_signal = coinbase_ws_service.symbol_signal(upper)
        if ws_signal:
            selected_sources.append("COINBASE_WS_PUBLIC")
            sentiment_score = max(-1.0, min((sentiment_score * 0.7) + (float(ws_signal["sentiment_score"]) * 0.3), 1.0))
            news_momentum_score = max(float(news_momentum_score), float(ws_signal["news_momentum_score"]))
            event_strength = max(float(event_strength), float(ws_signal["event_strength"]))
            for flag in ws_signal.get("event_flags", []):
                if flag not in event_flags:
                    event_flags.append(flag)

        data_classification = "PUBLIC"
        rationale = (
            "Signals derived from Alpaca public news and Coinbase public websocket market feed; "
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

    def _score_article(self, article: dict) -> tuple[float, str | None]:
        headline = f"{article.get('headline', '')} {article.get('summary', '')}".lower()
        positive_terms = ["beats", "surge", "growth", "upgrade", "wins", "record", "profit"]
        negative_terms = ["misses", "drop", "lawsuit", "downgrade", "cuts", "loss", "probe"]
        event_terms = {
            "earnings": "EARNINGS_EVENT",
            "guidance": "GUIDANCE_UPDATE",
            "merger": "CORPORATE_ACTION",
            "acquisition": "CORPORATE_ACTION",
            "fed": "MACRO_EVENT",
            "sec": "REGULATORY_EVENT",
        }

        positive_hits = sum(term in headline for term in positive_terms)
        negative_hits = sum(term in headline for term in negative_terms)
        score = 0.18 * positive_hits - 0.18 * negative_hits
        flag = next((value for term, value in event_terms.items() if term in headline), None)
        return max(-1.0, min(score, 1.0)), flag

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
