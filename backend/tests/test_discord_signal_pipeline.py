"""
Integration tests for the Discord signal pipeline.

Coverage:
  - Symbol extraction from raw message content
  - Options signal parsing (CALL/PUT with strike and expiry)
  - Blocked noise-word filter
  - _build_snapshot(): guild filter, channel filter, combined filter
  - TTL cache invalidation
  - Watchlist pin/unpin
  - inject_symbols_from_event() auto-pins with 'discord' source
  - Scanner inject: _discord_priority_symbols() returns union of symbols + pinned
  - Guild filter: multi-guild comma-separated config
  - Channel filter: multi-channel comma-separated config
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

# ---------------------------------------------------------------------------
# Bootstrap: temp SQLite DB + required env vars before any app imports
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"
os.environ.setdefault("AUTH_SESSION_SECRET", "test-secret-key-discord-test")
os.environ.setdefault("DISCORD_INBOUND_ENABLED", "true")
os.environ.setdefault("DISCORD_PUBLIC_KEY", "a" * 64)  # fake but valid-length hex

from app.db.init_db import initialize_database  # noqa: E402
from app.db.models import DiscordInboundEvent, DiscordSignalWatchlist  # noqa: E402
from app.db.session import get_session  # noqa: E402

initialize_database()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _insert_event(
    content: str,
    symbols: list[str],
    guild_id: str = "SERVER_A",
    channel_id: str = "CHAN_1",
    minutes_ago: int = 5,
) -> int:
    """Insert a fake DiscordInboundEvent and return its id."""
    ts = datetime.now(tz=timezone.utc) - timedelta(minutes=minutes_ago)
    with get_session() as session:
        row = DiscordInboundEvent(
            payload_json=json.dumps({"content": content}),
            event_type="MESSAGE_CREATE",
            guild_id=guild_id,
            channel_id=channel_id,
            content=content,
            extracted_symbols=json.dumps(symbols),
            created_at=ts,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row.id


def _clear_events() -> None:
    with get_session() as session:
        session.query(DiscordInboundEvent).delete()
        session.query(DiscordSignalWatchlist).delete()
        session.commit()


# ---------------------------------------------------------------------------
# Import service AFTER DB is ready
# ---------------------------------------------------------------------------
from app.services.discord_signal_service import (  # noqa: E402
    DiscordSignalService,
    _BLOCKED,
    _OPTIONS_RE,
    _SYMBOL_RE,
    _is_eligible,
)
from app.core import config as _config_module  # noqa: E402


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSymbolExtraction(unittest.TestCase):
    """Unit tests for the regex and blocked-word filter — no DB required."""

    def _extract(self, text: str) -> list[str]:
        raw = _SYMBOL_RE.findall(text.upper())
        return [s for s in raw if s not in _BLOCKED and _is_eligible(s)]

    def test_dollar_prefix(self):
        result = self._extract("Buying $AAPL and $TSLA today")
        self.assertIn("AAPL", result)
        self.assertIn("TSLA", result)

    def test_hash_prefix(self):
        result = self._extract("#SPY is looking strong")
        self.assertIn("SPY", result)

    def test_bare_ticker(self):
        result = self._extract("NVDA broke out above resistance")
        self.assertIn("NVDA", result)

    def test_blocked_words_excluded(self):
        result = self._extract("BUY CALL PUT HOLD THE AND FOR")
        self.assertEqual(result, [])

    def test_mixed(self):
        result = self._extract("$MSFT calls are cheap, also watching AMZN and FOR the record")
        self.assertIn("MSFT", result)
        self.assertIn("AMZN", result)
        self.assertNotIn("FOR", result)

    def test_too_long_ticker_excluded(self):
        result = self._extract("TOOLONG is not a ticker")
        self.assertNotIn("TOOLONG", result)


class TestOptionsRegex(unittest.TestCase):
    """Unit tests for the options signal pattern."""

    def _parse(self, text: str):
        return list(_OPTIONS_RE.finditer(text))

    def test_full_call_with_strike_and_expiry(self):
        matches = self._parse("AAPL $200 5/16 calls")
        self.assertEqual(len(matches), 1)
        m = matches[0]
        self.assertEqual(m.group("symbol"), "AAPL")
        self.assertIn(m.group("direction").lower(), ("call", "calls"))
        self.assertEqual(m.group("strike"), "200")
        self.assertIsNotNone(m.group("expiry"))

    def test_put_no_strike(self):
        matches = self._parse("TSLA puts")
        self.assertEqual(len(matches), 1)
        self.assertIn(matches[0].group("direction").lower(), ("put", "puts"))

    def test_multiple_signals(self):
        matches = self._parse("NVDA $900 calls and MSFT $400 puts")
        self.assertEqual(len(matches), 2)
        symbols = {m.group("symbol") for m in matches}
        self.assertIn("NVDA", symbols)
        self.assertIn("MSFT", symbols)

    def test_no_match_on_plain_ticker(self):
        matches = self._parse("Watching AAPL and SPY today")
        self.assertEqual(len(matches), 0)


class TestSnapshotFiltering(unittest.TestCase):
    """Integration tests: _build_snapshot with guild/channel filters."""

    def setUp(self):
        _clear_events()

    def _make_service(self, guild_ids: str = "", channels: str = "") -> DiscordSignalService:
        """Return a fresh DiscordSignalService with custom filter config."""
        svc = DiscordSignalService()
        # Patch settings on the module-level settings object temporarily
        svc._test_guild_ids = guild_ids
        svc._test_channels = channels

        # Monkey-patch the helpers on this instance
        svc._allowed_guilds = lambda: (  # type: ignore[method-assign]
            {g.strip() for g in guild_ids.split(",") if g.strip()} if guild_ids else set()
        )
        svc._allowed_channels = lambda: (  # type: ignore[method-assign]
            {c.strip() for c in channels.split(",") if c.strip()} if channels else set()
        )
        return svc

    def test_no_filters_accepts_all(self):
        _insert_event("$AAPL calls", ["AAPL"], guild_id="G1", channel_id="C1")
        _insert_event("$TSLA puts", ["TSLA"], guild_id="G2", channel_id="C2")
        svc = self._make_service()
        snap = svc._build_snapshot()
        self.assertIn("AAPL", snap.symbols)
        self.assertIn("TSLA", snap.symbols)

    def test_guild_filter_allows_matching(self):
        _insert_event("$SPY calls", ["SPY"], guild_id="SERVER_A", channel_id="C1")
        _insert_event("$QQQ puts", ["QQQ"], guild_id="SERVER_B", channel_id="C1")
        svc = self._make_service(guild_ids="SERVER_A")
        snap = svc._build_snapshot()
        self.assertIn("SPY", snap.symbols)
        self.assertNotIn("QQQ", snap.symbols)

    def test_guild_filter_multi_guild(self):
        _insert_event("$SPY calls", ["SPY"], guild_id="SERVER_A")
        _insert_event("$QQQ puts", ["QQQ"], guild_id="SERVER_B")
        _insert_event("$IWM calls", ["IWM"], guild_id="SERVER_C")
        svc = self._make_service(guild_ids="SERVER_A,SERVER_B")
        snap = svc._build_snapshot()
        self.assertIn("SPY", snap.symbols)
        self.assertIn("QQQ", snap.symbols)
        self.assertNotIn("IWM", snap.symbols)

    def test_channel_filter_allows_matching(self):
        _insert_event("$NVDA calls", ["NVDA"], guild_id="G1", channel_id="CHAN_SIGNALS")
        _insert_event("$AMD puts", ["AMD"], guild_id="G1", channel_id="CHAN_GENERAL")
        svc = self._make_service(channels="CHAN_SIGNALS")
        snap = svc._build_snapshot()
        self.assertIn("NVDA", snap.symbols)
        self.assertNotIn("AMD", snap.symbols)

    def test_channel_filter_multi_channel(self):
        _insert_event("$MSFT calls", ["MSFT"], channel_id="CHAN_1")
        _insert_event("$GOOG calls", ["GOOG"], channel_id="CHAN_2")
        _insert_event("$AMZN calls", ["AMZN"], channel_id="CHAN_3")
        svc = self._make_service(channels="CHAN_1,CHAN_2")
        snap = svc._build_snapshot()
        self.assertIn("MSFT", snap.symbols)
        self.assertIn("GOOG", snap.symbols)
        self.assertNotIn("AMZN", snap.symbols)

    def test_combined_guild_and_channel_filter(self):
        # Must match BOTH guild and channel
        _insert_event("$META calls", ["META"], guild_id="SERVER_A", channel_id="CHAN_SIGNALS")
        _insert_event("$NFLX calls", ["NFLX"], guild_id="SERVER_A", channel_id="CHAN_GENERAL")
        _insert_event("$ORCL calls", ["ORCL"], guild_id="SERVER_B", channel_id="CHAN_SIGNALS")
        svc = self._make_service(guild_ids="SERVER_A", channels="CHAN_SIGNALS")
        snap = svc._build_snapshot()
        self.assertIn("META", snap.symbols)       # ✓ right guild + right channel
        self.assertNotIn("NFLX", snap.symbols)    # ✗ right guild, wrong channel
        self.assertNotIn("ORCL", snap.symbols)    # ✗ wrong guild, right channel

    def test_old_events_excluded_by_window(self):
        # Insert event 48 hours ago — outside a 24h window
        _insert_event("$OLD calls", ["OLD"], minutes_ago=48 * 60)
        svc = DiscordSignalService()
        svc._window_hours = lambda: 24  # type: ignore[method-assign]
        svc._allowed_guilds = lambda: set()  # type: ignore[method-assign]
        svc._allowed_channels = lambda: set()  # type: ignore[method-assign]
        snap = svc._build_snapshot()
        self.assertNotIn("OLD", snap.symbols)

    def test_options_signals_parsed_from_content(self):
        _insert_event("AAPL $200 5/16 calls", ["AAPL"])
        svc = self._make_service()
        snap = svc._build_snapshot()
        directions = {sig.direction for sig in snap.options_signals}
        symbols_in_opts = {sig.symbol for sig in snap.options_signals}
        self.assertIn("AAPL", symbols_in_opts)
        self.assertIn("CALL", directions)


class TestWatchlistPinUnpin(unittest.TestCase):
    """DB-backed watchlist operations."""

    def setUp(self):
        _clear_events()
        self.svc = DiscordSignalService()

    def test_pin_and_unpin(self):
        self.svc.pin_symbol("HOOD", asset_class="equity", note="test pin")
        entries = self.svc.pinned_entries()
        symbols = [e.symbol for e in entries]
        self.assertIn("HOOD", symbols)

        self.svc.unpin_symbol("HOOD")
        entries_after = self.svc.pinned_entries()
        self.assertNotIn("HOOD", [e.symbol for e in entries_after])

    def test_pin_duplicate_is_idempotent(self):
        self.svc.pin_symbol("COIN", asset_class="crypto")
        self.svc.pin_symbol("COIN", asset_class="crypto")  # second call should not raise
        entries = self.svc.pinned_entries()
        count = sum(1 for e in entries if e.symbol == "COIN")
        self.assertEqual(count, 1)

    def test_inject_symbols_from_event_pins_with_discord_source(self):
        self.svc.inject_symbols_from_event(["RBLX", "U"])
        entries = self.svc.pinned_entries()
        symbols = {e.symbol for e in entries}
        sources = {e.source for e in entries if e.symbol in ("RBLX", "U")}
        self.assertIn("RBLX", symbols)
        self.assertIn("U", symbols)
        self.assertEqual(sources, {"discord_event"})


class TestCacheInvalidation(unittest.TestCase):
    """TTL cache is invalidated on demand."""

    def setUp(self):
        _clear_events()

    def test_invalidate_cache_clears_snapshot(self):
        svc = DiscordSignalService()
        # Prime cache
        _ = svc.active_snapshot()
        self.assertIsNotNone(svc._cache)
        # Invalidate
        svc.invalidate_cache()
        self.assertIsNone(svc._cache)

    def test_stale_cache_rebuilt_after_invalidate(self):
        svc = DiscordSignalService()
        snap1 = svc.active_snapshot()
        self.assertEqual(snap1.symbols, [])

        _insert_event("$CRWD calls", ["CRWD"])
        svc.invalidate_cache()
        snap2 = svc.active_snapshot()
        self.assertIn("CRWD", snap2.symbols)


if __name__ == "__main__":
    unittest.main(verbosity=2)
