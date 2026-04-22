"""
Discord Signal Service
======================
Bridges Discord inbound events to the trading scanner.

Responsibilities:
- Read recent DiscordInboundEvents and extract active ticker symbols
- Filter to trusted signal channels if configured
- Parse options-specific language (calls, puts, strikes, expiry)
- Maintain an operator-pinned watchlist (DiscordSignalWatchlist)
- Expose a unified "active signals" snapshot consumed by the scanner
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any

from sqlalchemy import delete, select

from app.core.config import settings
from app.db.models import DiscordInboundEvent, DiscordSignalWatchlist
from app.db.session import get_session


# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Ticker symbols: 1-5 uppercase letters, optionally preceded by $ or # (e.g. $AAPL, #SPY)
_SYMBOL_RE = re.compile(r"(?:[$#]?)(?<!\w)([A-Z]{1,5})(?!\w)")

# Noise words that look like tickers but aren't
_BLOCKED: frozenset[str] = frozenset({
    "A", "I", "AN", "AS", "AT", "BE", "BY", "DO", "GO", "IF", "IN", "IS",
    "IT", "ME", "MY", "NO", "OF", "ON", "OR", "SO", "TO", "UP", "US", "WE",
    "THE", "AND", "FOR", "ARE", "BUT", "NOT", "YET", "ITS", "HAS", "HAD",
    "WAS", "DID", "GET", "GOT", "LET", "NEW", "OLD", "BIG", "TOP", "LOW",
    "HIGH", "ALL", "ANY", "CAN", "MAY", "NOW", "HOW", "WHO", "WHY", "TWO",
    "ONE", "USE", "OUT", "OFF", "OUR", "TOO", "DUE", "RUN", "SET", "FAR",
    "CALL", "PUT", "BUY", "SELL", "LONG", "SHORT", "BEAR", "BULL",
    "HOLD", "STOP", "LOSS", "GAIN", "RISK", "OPEN", "CASH", "FLOW",
    "RATE", "FLAT", "RISE", "FALL", "MOVE", "HELP", "NOTE", "WAIT",
    "GOOD", "BEST", "NICE", "SAFE", "FAST", "HUGE", "LAST", "NEXT",
    "NEWS", "INFO", "LIVE", "FREE", "FULL", "HARD", "REAL", "SOON",
    "PLAY", "GAME", "WEEK", "YEAR", "DAY", "EOD", "EOW", "YTD",
    "THIS", "THAT", "WITH", "FROM", "ALSO", "JUST", "BEEN", "WILL",
    "OVER", "LOOK", "BACK", "INTO", "THAN", "THEN", "THEY", "WHEN",
    "WHAT", "WENT", "SAID", "SAYS", "SEEM", "SHOW", "EACH", "BOTH",
    "MORE", "MUCH", "MOST", "MANY", "SOME", "LESS", "EVEN", "ONLY",
    "VERY", "WELL", "SAME", "SURE", "HAVE", "MAKE", "TAKE", "LIKE",
    "KNOW", "COME", "GIVE", "WANT", "NEED", "FEEL", "SEEM", "MEAN",
    "ELSE", "THUS", "TILL", "UPON", "AMID", "AMID", "THRU", "THRU",
    "IPO", "ETF", "OTC", "OTM", "ITM", "ATM", "DTE", "IV",
    "YOLO", "FOMO", "HODL", "REKT", "MOON", "DUMP", "PUMP", "DEGEN",
    "ALERT", "SIGNAL", "TRADE", "ENTRY", "EXIT", "TARGET", "STOP",
    "PRICE", "CLOSE", "ABOVE", "BELOW", "CHART", "LEVEL", "BREAK",
    "TREND", "SETUP", "WATCH", "IDEA",
})

# Options language patterns
_OPTIONS_RE = re.compile(
    r"""(?ix)
    (?P<symbol>[A-Z]{1,5})            # ticker
    \s+
    (?:\$(?P<strike>\d+(?:\.\d+)?)    # optional $strike
    \s+)?
    (?P<expiry>
        \d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?  # date e.g. 5/16 or 05/16/25
        |
        (?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{2,4})?
    )?
    \s*
    (?P<direction>call|calls|put|puts)  # required direction
    """,
    re.IGNORECASE,
)


@dataclass
class OptionsSignal:
    symbol: str
    direction: str          # "CALL" | "PUT"
    strike: float | None
    expiry_raw: str | None


@dataclass
class DiscordSignalSnapshot:
    symbols: list[str]
    options_signals: list[OptionsSignal]
    pinned_symbols: list[str]
    source_counts: dict[str, int]
    generated_at: datetime
    window_hours: int


@dataclass
class PinnedSymbolEntry:
    symbol: str
    asset_class: str
    source: str
    note: str | None
    pinned_by: str | None
    pinned_at: datetime


_CACHE_TTL_SECONDS = 30


class DiscordSignalService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._cache: DiscordSignalSnapshot | None = None
        self._cache_at: datetime | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_enabled(self) -> bool:
        return bool(settings.discord_inbound_enabled) and self._window_hours() > 0

    def active_snapshot(self) -> DiscordSignalSnapshot:
        """Return cached (≤30 s) snapshot of active Discord-sourced symbols."""
        now = datetime.now(tz=timezone.utc)
        with self._lock:
            if (
                self._cache is not None
                and self._cache_at is not None
                and (now - self._cache_at).total_seconds() < _CACHE_TTL_SECONDS
            ):
                return self._cache

        snapshot = self._build_snapshot()
        with self._lock:
            self._cache = snapshot
            self._cache_at = now
        return snapshot

    def invalidate_cache(self) -> None:
        with self._lock:
            self._cache = None
            self._cache_at = None

    def pinned_entries(self) -> list[PinnedSymbolEntry]:
        with get_session() as session:
            rows = session.execute(
                select(DiscordSignalWatchlist).order_by(DiscordSignalWatchlist.pinned_at.desc())
            ).scalars().all()
            return [
                PinnedSymbolEntry(
                    symbol=row.symbol,
                    asset_class=row.asset_class,
                    source=row.source,
                    note=row.note,
                    pinned_by=row.pinned_by,
                    pinned_at=row.pinned_at,
                )
                for row in rows
            ]

    def pin_symbol(
        self,
        symbol: str,
        *,
        asset_class: str = "equity",
        source: str = "manual",
        note: str | None = None,
        pinned_by: str | None = None,
    ) -> PinnedSymbolEntry:
        upper = symbol.strip().upper()
        with get_session() as session:
            row = session.execute(
                select(DiscordSignalWatchlist).where(DiscordSignalWatchlist.symbol == upper)
            ).scalar_one_or_none()
            if row is None:
                row = DiscordSignalWatchlist(symbol=upper)
                session.add(row)
            row.asset_class = asset_class
            row.source = source
            row.note = note
            row.pinned_by = pinned_by
            row.pinned_at = datetime.now(tz=timezone.utc)
        self.invalidate_cache()
        return PinnedSymbolEntry(
            symbol=upper,
            asset_class=asset_class,
            source=source,
            note=note,
            pinned_by=pinned_by,
            pinned_at=datetime.now(tz=timezone.utc),
        )

    def unpin_symbol(self, symbol: str) -> bool:
        upper = symbol.strip().upper()
        with get_session() as session:
            result = session.execute(
                delete(DiscordSignalWatchlist).where(DiscordSignalWatchlist.symbol == upper)
            )
            deleted = bool(result.rowcount)
        self.invalidate_cache()
        return deleted

    def inject_symbols_from_event(self, symbols: list[str], *, source: str = "discord_event") -> None:
        """Auto-pin symbols extracted from a fresh Discord event into watchlist."""
        if not symbols:
            return
        for sym in symbols[:settings.discord_signal_max_inject]:
            try:
                self.pin_symbol(sym, asset_class=_infer_asset_class(sym), source=source)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _window_hours(self) -> int:
        return max(0, int(settings.discord_signal_window_hours or 0))

    def _allowed_channels(self) -> set[str]:
        raw = str(settings.discord_signal_channels or "").strip()
        if not raw:
            return set()
        return {c.strip() for c in raw.split(",") if c.strip()}

    def _allowed_guilds(self) -> set[str]:
        raw = str(settings.discord_signal_guild_ids or "").strip()
        if not raw:
            return set()
        return {g.strip() for g in raw.split(",") if g.strip()}

    def _build_snapshot(self) -> DiscordSignalSnapshot:
        now = datetime.now(tz=timezone.utc)
        window_hours = self._window_hours()
        since = now - timedelta(hours=window_hours)
        allowed_guilds = self._allowed_guilds()
        allowed_channels = self._allowed_channels()

        raw_events: list[dict[str, Any]] = []
        with get_session() as session:
            rows = session.execute(
                select(DiscordInboundEvent).where(DiscordInboundEvent.created_at >= since)
            ).scalars().all()
            for row in rows:
                # Primary filter: server/guild ID (if configured)
                if allowed_guilds and row.guild_id not in allowed_guilds:
                    continue
                # Secondary filter: specific channel IDs (if configured)
                if allowed_channels and row.channel_id not in allowed_channels:
                    continue
                try:
                    syms = json.loads(row.extracted_symbols or "[]")
                except json.JSONDecodeError:
                    syms = []
                raw_events.append({
                    "symbols": [str(s).upper() for s in syms if str(s).strip()],
                    "content": row.content or "",
                    "channel_id": row.channel_id,
                    "created_at": row.created_at,
                })

        # Aggregate symbols with recency weighting
        symbol_mentions: dict[str, int] = {}
        options_signals: list[OptionsSignal] = []
        for event in raw_events:
            for sym in event["symbols"]:
                if sym in _BLOCKED or not _is_eligible(sym):
                    continue
                symbol_mentions[sym] = symbol_mentions.get(sym, 0) + 1
            # Parse options signals from full content
            for match in _OPTIONS_RE.finditer(event["content"]):
                sym = match.group("symbol").upper()
                if sym in _BLOCKED or not _is_eligible(sym):
                    continue
                direction = match.group("direction").upper()
                if direction.endswith("S"):
                    direction = direction[:-1]  # "CALLS" -> "CALL"
                strike_raw = match.group("strike")
                expiry_raw = match.group("expiry")
                options_signals.append(OptionsSignal(
                    symbol=sym,
                    direction=direction,
                    strike=float(strike_raw) if strike_raw else None,
                    expiry_raw=expiry_raw,
                ))
                symbol_mentions[sym] = symbol_mentions.get(sym, 0) + 2  # options = extra weight

        # Sort by mention frequency; cap at max_inject
        max_inject = max(1, int(settings.discord_signal_max_inject or 20))
        sorted_symbols = sorted(symbol_mentions.keys(), key=lambda s: -symbol_mentions[s])[:max_inject]

        # Pinned watchlist symbols
        pinned_symbols: list[str] = []
        with get_session() as session:
            rows = session.execute(
                select(DiscordSignalWatchlist).order_by(DiscordSignalWatchlist.pinned_at.desc())
            ).scalars().all()
            pinned_symbols = [row.symbol for row in rows]

        source_counts: dict[str, int] = {}
        if sorted_symbols:
            source_counts["discord_events"] = len(sorted_symbols)
        if pinned_symbols:
            source_counts["pinned"] = len(pinned_symbols)

        return DiscordSignalSnapshot(
            symbols=sorted_symbols,
            options_signals=options_signals,
            pinned_symbols=pinned_symbols,
            source_counts=source_counts,
            generated_at=now,
            window_hours=window_hours,
        )


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------

_CRYPTO_SUFFIXES = {"USD", "BTC", "ETH", "USDT", "USDC"}


def _infer_asset_class(symbol: str) -> str:
    upper = symbol.upper()
    for suffix in _CRYPTO_SUFFIXES:
        if upper.endswith(suffix) and upper != suffix:
            return "crypto"
    return "equity"


def _is_eligible(symbol: str) -> bool:
    if not symbol:
        return False
    if len(symbol) > 6:
        return False
    if not re.match(r"^[A-Z]{1,6}$", symbol):
        return False
    return True


discord_signal_service = DiscordSignalService()
