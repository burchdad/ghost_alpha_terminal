from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html import unescape
import re
from threading import Lock
import xml.etree.ElementTree as ET

import httpx

from app.core.config import settings
from app.services.alpaca_client import alpaca_client
from app.services.news.coinbase_ws_service import coinbase_ws_service
from app.services.news_feed_settings_service import news_feed_settings_service


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


@dataclass
class NewsHeadline:
    source: str
    title: str
    url: str
    published_at: datetime | None
    summary: str
    relevance: float


@dataclass
class NewsSourceStatus:
    source: str
    url: str
    status: str
    headline_count: int
    weight: float
    last_success_at: datetime | None
    last_error: str | None


class NewsIntelligenceService:
    """Public-source news/sentiment layer with source whitelisting and audit trail."""

    _PUBLIC_FEEDS: tuple[dict[str, str], ...] = (
        {"source": "CNBC_TOP_NEWS", "url": "https://www.cnbc.com/id/100003114/device/rss/rss.html"},
        {"source": "MARKETWATCH_TOP_STORIES", "url": "http://feeds.marketwatch.com/marketwatch/topstories/"},
        {"source": "MARKETWATCH_MARKET_PULSE", "url": "http://feeds.marketwatch.com/marketwatch/marketpulse/"},
        {"source": "YAHOO_FINANCE_PUBLIC", "url": "https://finance.yahoo.com/news/rssindex"},
        {"source": "CNN_BUSINESS", "url": "http://rss.cnn.com/rss/money_latest.rss"},
        {"source": "NBC_BUSINESS", "url": "https://feeds.nbcnews.com/nbcnews/public/business"},
        {"source": "CSPAN_CONGRESS", "url": "https://www.c-span.org/rss/?id=General"},
        {"source": "SEC_PRESS_RELEASES", "url": "https://www.sec.gov/rss/news/press.xml"},
        {"source": "SEC_LITIGATION", "url": "https://www.sec.gov/rss/litigation/litreleases.xml"},
        {"source": "FED_RELEASES", "url": "https://www.federalreserve.gov/feeds/press_all.xml"},
        {"source": "NASDAQ_MARKETS", "url": "https://www.nasdaq.com/feed/rssoutbound?category=Markets"},
        {"source": "NYSE_MARKETS", "url": "https://www.nyse.com/rss/markets"},
    )

    _SYMBOL_TERMS: dict[str, tuple[str, ...]] = {
        "SPY": ("s&p 500", "stocks", "wall street", "equities", "market", "nasdaq", "dow"),
        "QQQ": ("nasdaq", "big tech", "megacap", "growth stocks", "tech stocks"),
        "DIA": ("dow", "blue chip", "industrial average"),
        "IWM": ("small caps", "russell 2000"),
        "BTCUSD": ("bitcoin", "btc", "crypto", "digital asset"),
        "ETHUSD": ("ethereum", "ether", "eth", "crypto"),
        "SOLUSD": ("solana", "sol", "crypto"),
    }

    _GENERIC_MARKET_TERMS: tuple[str, ...] = (
        "stocks",
        "markets",
        "wall street",
        "earnings",
        "fed",
        "interest rates",
        "inflation",
        "treasury",
        "economy",
        "equities",
        "etf",
        "options",
        "crypto",
    )

    def __init__(self) -> None:
        self._lock = Lock()
        self._audit: list[NewsAuditEntry] = []
        self._max_audit = 1000
        self._cache_ttl_seconds = 20
        self._cache: dict[str, tuple[datetime, dict]] = {}
        self._feed_cache_ttl_seconds = max(30, int(settings.news_feed_refresh_seconds or 90))
        self._feed_cache: tuple[datetime, list[NewsHeadline], list[NewsSourceStatus]] | None = None
        self._alpaca_news_cooldown_until: datetime | None = None

    def source_whitelist(self) -> list[str]:
        return ["ALPACA_NEWS", "COINBASE_WS_PUBLIC", *[feed["source"] for feed in self._configured_public_feeds()]]

    def public_feed_catalog(self) -> list[dict[str, str]]:
        return [dict(feed) for feed in self._PUBLIC_FEEDS]

    def invalidate_cached_feeds(self) -> None:
        with self._lock:
            self._feed_cache = None
            self._cache.clear()

    def headlines(self, *, symbol: str | None = None, limit: int = 30) -> dict:
        normalized = symbol.upper() if symbol else None
        headlines, source_status = self._load_public_feed_bundle()
        filtered = self._filter_headlines(headlines, symbol=normalized, limit=limit)
        return {
            "headlines": [self._serialize_headline(item) for item in filtered],
            "source_status": [self._serialize_source_status(item) for item in source_status],
        }

    def dashboard(self, *, symbol: str, limit: int = 25) -> dict:
        signal = self.analyze_symbol(symbol)
        headline_bundle = self.headlines(symbol=symbol, limit=limit)
        return {
            "signal": signal,
            "headlines": headline_bundle["headlines"],
            "audit": self.recent_audit(limit=min(max(limit, 10), 40)),
            "sources": self.source_whitelist(),
            "source_status": headline_bundle["source_status"],
            "stream_status": coinbase_ws_service.status(),
        }

    def analyze_symbol(self, symbol: str) -> dict:
        upper = symbol.upper()
        now = datetime.now(tz=timezone.utc)

        with self._lock:
            cached = self._cache.get(upper)
            if cached and (now - cached[0]).total_seconds() <= self._cache_ttl_seconds:
                return dict(cached[1])

        selected_sources: list[str] = []
        articles: list[dict] = []
        sentiment_score = 0.0
        news_momentum_score = 0.0
        event_strength = 0.0
        event_flags: list[str] = []

        public_bundle = self.headlines(symbol=upper, limit=12)
        public_headlines = public_bundle["headlines"]
        public_sentiment = 0.0
        public_momentum = 0.0
        public_strength = 0.0
        public_weight = 0.0
        if public_headlines:
            public_scores: list[tuple[float, str | None]] = []
            public_sources = sorted({str(item["source"]) for item in public_headlines})
            public_total_weight = 0.0
            for headline in public_headlines:
                score, headline_flag = self._score_text(f"{headline.get('title', '')} {headline.get('summary', '')}")
                source_weight = self._source_weight(str(headline.get("source", "")))
                public_scores.append((score * source_weight, headline_flag))
                public_total_weight += source_weight
                if headline_flag and headline_flag not in event_flags:
                    event_flags.append(headline_flag)
            public_sentiment = sum(score for score, _ in public_scores) / max(public_total_weight, 1.0)
            public_momentum = min(1.0, len(public_headlines) / 8.0)
            public_strength = max(abs(public_sentiment), public_momentum)
            public_weight = max(0.25, min(public_total_weight / max(len(public_headlines), 1), 1.5))
            selected_sources.extend(public_sources)
            if len(public_headlines) >= 5:
                event_flags.append("PUBLIC_HEADLINE_CLUSTER")
            if public_momentum >= 0.75:
                event_flags.append("PUBLIC_NEWS_VELOCITY")

        cooldown_active = False
        with self._lock:
            if self._alpaca_news_cooldown_until and now < self._alpaca_news_cooldown_until:
                cooldown_active = True

        if cooldown_active:
            event_flags.append("ALPACA_NEWS_COOLDOWN")
        else:
            try:
                articles = alpaca_client.get_news(symbol=upper, limit=10)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    with self._lock:
                        self._alpaca_news_cooldown_until = datetime.now(tz=timezone.utc).replace(microsecond=0)
                    event_flags.append("ALPACA_NEWS_RATE_LIMITED")
                else:
                    event_flags.append("ALPACA_NEWS_HTTP_ERROR")
            except Exception:
                event_flags.append("ALPACA_NEWS_UNAVAILABLE")

        # If we set cooldown due to 429, skip Alpaca for 2 minutes.
        if "ALPACA_NEWS_RATE_LIMITED" in event_flags:
            with self._lock:
                self._alpaca_news_cooldown_until = datetime.now(tz=timezone.utc) + timedelta(seconds=120)

        alpaca_sentiment = 0.0
        alpaca_momentum = 0.0
        alpaca_strength = 0.0
        alpaca_weight = 0.0
        if articles:
            article_scores = [self._score_article(article) for article in articles]
            alpaca_sentiment = sum(score for score, _ in article_scores) / len(article_scores)
            alpaca_momentum = min(1.0, len(articles) / 10.0)
            alpaca_strength = max(abs(alpaca_sentiment), alpaca_momentum)
            alpaca_weight = max(0.25, self._source_weight("ALPACA_NEWS"))
            selected_sources.append("ALPACA_NEWS")
            if len(articles) >= 6:
                event_flags.append("HEADLINE_CLUSTER")
            if alpaca_momentum >= 0.7:
                event_flags.append("NEWS_VELOCITY_SPIKE")
            if abs(alpaca_sentiment) >= 0.45:
                event_flags.append("SENTIMENT_EXTREME")
            for _, article_flag in article_scores:
                if article_flag and article_flag not in event_flags:
                    event_flags.append(article_flag)
        else:
            if "ALPACA_NEWS_RATE_LIMITED" not in event_flags:
                event_flags.append("NO_RECENT_ALPACA_NEWS")

        total_weight = public_weight + alpaca_weight
        if total_weight > 0.0:
            sentiment_score = ((public_sentiment * public_weight) + (alpaca_sentiment * alpaca_weight)) / total_weight
            news_momentum_score = ((public_momentum * public_weight) + (alpaca_momentum * alpaca_weight)) / total_weight
            event_strength = max(public_strength, alpaca_strength)

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
            "Signals derived from public market-news feeds, Alpaca public news, and Coinbase public websocket market feed; "
            "no private channels or restricted datasets included."
        )
        deduped_sources = list(dict.fromkeys(selected_sources))
        deduped_flags = list(dict.fromkeys(event_flags))

        analysis = {
            "symbol": upper,
            "timestamp": datetime.now(tz=timezone.utc),
            "data_classification": data_classification,
            "sources_used": deduped_sources,
            "sentiment_score": round(sentiment_score, 6),
            "news_momentum_score": round(news_momentum_score, 6),
            "event_strength": round(event_strength, 6),
            "event_flags": deduped_flags,
            "rationale": rationale,
        }

        self._record(
            NewsAuditEntry(
                timestamp=datetime.now(tz=timezone.utc),
                symbol=upper,
                data_classification=data_classification,
                sources_used=deduped_sources,
                sentiment_score=round(sentiment_score, 6),
                news_momentum_score=round(news_momentum_score, 6),
                event_strength=round(event_strength, 6),
                event_flags=deduped_flags,
            )
        )

        with self._lock:
            self._cache[upper] = (datetime.now(tz=timezone.utc), analysis)

        return analysis

    def _score_article(self, article: dict) -> tuple[float, str | None]:
        headline = f"{article.get('headline', '')} {article.get('summary', '')}"
        return self._score_text(headline)

    def _score_text(self, text: str) -> tuple[float, str | None]:
        headline = text.lower()
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

    def _load_public_feed_bundle(self) -> tuple[list[NewsHeadline], list[NewsSourceStatus]]:
        now = datetime.now(tz=timezone.utc)
        with self._lock:
            if self._feed_cache and (now - self._feed_cache[0]).total_seconds() <= self._feed_cache_ttl_seconds:
                return list(self._feed_cache[1]), list(self._feed_cache[2])

        headlines: list[NewsHeadline] = []
        source_status: list[NewsSourceStatus] = []
        for feed in self._configured_public_feeds():
            source = feed["source"]
            url = feed["url"]
            weight = self._source_weight(source)
            try:
                feed_headlines = self._fetch_feed(url=url, source=source)
                headlines.extend(feed_headlines)
                source_status.append(
                    NewsSourceStatus(
                        source=source,
                        url=url,
                        status="ok",
                        headline_count=len(feed_headlines),
                        weight=weight,
                        last_success_at=now,
                        last_error=None,
                    )
                )
            except Exception as exc:
                source_status.append(
                    NewsSourceStatus(
                        source=source,
                        url=url,
                        status="error",
                        headline_count=0,
                        weight=weight,
                        last_success_at=None,
                        last_error=str(exc)[:160],
                    )
                )

        deduped: dict[str, NewsHeadline] = {}
        for item in sorted(
            headlines,
            key=lambda headline: headline.published_at or datetime.fromtimestamp(0, tz=timezone.utc),
            reverse=True,
        ):
            dedupe_key = f"{item.source}:{item.title.strip().lower()}"
            if dedupe_key not in deduped:
                deduped[dedupe_key] = item

        cached_headlines = list(deduped.values())[:250]
        with self._lock:
            self._feed_cache = (now, cached_headlines, source_status)
        return cached_headlines, source_status

    def _fetch_feed(self, *, url: str, source: str) -> list[NewsHeadline]:
        with httpx.Client(timeout=8.0, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "ghost-alpha-terminal/1.0"})
        response.raise_for_status()
        root = ET.fromstring(response.text)

        items = root.findall(".//item")
        entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")
        headlines: list[NewsHeadline] = []

        for item in items:
            title = self._clean_text(self._node_text(item.find("title")))
            link = self._clean_text(self._node_text(item.find("link")))
            summary = self._clean_text(self._node_text(item.find("description")))
            published_at = self._parse_datetime(self._node_text(item.find("pubDate")))
            if title and link:
                headlines.append(
                    NewsHeadline(
                        source=source,
                        title=title,
                        url=link,
                        published_at=published_at,
                        summary=summary,
                        relevance=0.0,
                    )
                )

        for entry in entries:
            title = self._clean_text(self._node_text(entry.find("{http://www.w3.org/2005/Atom}title")))
            link_node = entry.find("{http://www.w3.org/2005/Atom}link")
            link = ""
            if link_node is not None:
                link = self._clean_text(link_node.attrib.get("href", ""))
            summary = self._clean_text(self._node_text(entry.find("{http://www.w3.org/2005/Atom}summary")))
            if not summary:
                summary = self._clean_text(self._node_text(entry.find("{http://www.w3.org/2005/Atom}content")))
            published_at = self._parse_datetime(
                self._node_text(entry.find("{http://www.w3.org/2005/Atom}updated"))
                or self._node_text(entry.find("{http://www.w3.org/2005/Atom}published"))
            )
            if title and link:
                headlines.append(
                    NewsHeadline(
                        source=source,
                        title=title,
                        url=link,
                        published_at=published_at,
                        summary=summary,
                        relevance=0.0,
                    )
                )

        return headlines[:40]

    def _filter_headlines(self, headlines: list[NewsHeadline], *, symbol: str | None, limit: int) -> list[NewsHeadline]:
        if not headlines:
            return []

        scored: list[NewsHeadline] = []
        for item in headlines:
            relevance = self._headline_relevance(item=item, symbol=symbol)
            if symbol and relevance <= 0.0:
                continue
            scored.append(
                NewsHeadline(
                    source=item.source,
                    title=item.title,
                    url=item.url,
                    published_at=item.published_at,
                    summary=item.summary,
                    relevance=relevance,
                )
            )

        scored.sort(
            key=lambda item: (item.relevance, item.published_at or datetime.fromtimestamp(0, tz=timezone.utc)),
            reverse=True,
        )

        if symbol and len(scored) < limit:
            existing_titles = {row.title for row in scored}
            generic_fill = [item for item in headlines if item.title not in existing_titles]
            generic_fill.sort(
                key=lambda item: item.published_at or datetime.fromtimestamp(0, tz=timezone.utc),
                reverse=True,
            )
            scored.extend(
                NewsHeadline(
                    source=item.source,
                    title=item.title,
                    url=item.url,
                    published_at=item.published_at,
                    summary=item.summary,
                    relevance=max(0.05, self._headline_relevance(item=item, symbol=None)),
                )
                for item in generic_fill[: max(0, limit - len(scored))]
            )

        return scored[:limit]

    def _headline_relevance(self, *, item: NewsHeadline, symbol: str | None) -> float:
        text = f"{item.title} {item.summary}".lower()
        market_hits = sum(term in text for term in self._GENERIC_MARKET_TERMS)
        base_score = 0.15 * market_hits
        if not symbol:
            return min(1.0, max(base_score * self._source_weight(item.source), 0.1 if market_hits else 0.0))

        terms = {symbol.lower()}
        terms.update(self._SYMBOL_TERMS.get(symbol, ()))
        if symbol.endswith("USD") and len(symbol) > 3:
            terms.add(symbol[:-3].lower())
        term_hits = sum(term in text for term in terms)
        if term_hits == 0 and market_hits == 0:
            return 0.0
        return min(1.0, ((0.45 * term_hits) + base_score) * self._source_weight(item.source))

    def _configured_public_feeds(self) -> list[dict[str, str]]:
        runtime_settings = news_feed_settings_service.status()
        enabled = {item.strip().upper() for item in runtime_settings.get("enabled_sources", []) if str(item).strip()}
        if not enabled:
            return list(self._PUBLIC_FEEDS)
        return [feed for feed in self._PUBLIC_FEEDS if feed["source"] in enabled]

    def _source_weight_map(self) -> dict[str, float]:
        configured = news_feed_settings_service.status().get("source_weights", {})
        return {
            str(source).strip().upper(): max(0.1, min(float(weight), 10.0))
            for source, weight in configured.items()
            if str(source).strip()
        }

    def _source_weight(self, source: str) -> float:
        return float(self._source_weight_map().get(source.upper(), 1.0))

    @staticmethod
    def _node_text(node: ET.Element | None) -> str:
        if node is None or node.text is None:
            return ""
        return node.text

    @staticmethod
    def _clean_text(value: str) -> str:
        cleaned = unescape(re.sub(r"<[^>]+>", " ", value or ""))
        return re.sub(r"\s+", " ", cleaned).strip()

    @staticmethod
    def _parse_datetime(raw: str) -> datetime | None:
        if not raw:
            return None
        try:
            parsed = parsedate_to_datetime(raw)
            return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except Exception:
            try:
                parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except Exception:
                return None

    @staticmethod
    def _serialize_headline(item: NewsHeadline) -> dict:
        return {
            "source": item.source,
            "title": item.title,
            "url": item.url,
            "published_at": item.published_at,
            "summary": item.summary,
            "relevance": round(item.relevance, 4),
        }

    @staticmethod
    def _serialize_source_status(item: NewsSourceStatus) -> dict:
        return {
            "source": item.source,
            "url": item.url,
            "status": item.status,
            "headline_count": item.headline_count,
            "weight": round(item.weight, 3),
            "last_success_at": item.last_success_at,
            "last_error": item.last_error,
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
