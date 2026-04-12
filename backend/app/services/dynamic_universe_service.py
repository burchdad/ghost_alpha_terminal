from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx

from app.core.config import settings
from app.services.scan_health import logger


_SYMBOL_RE = re.compile(r"^[A-Z]{1,5}$")


@dataclass
class UniverseSnapshot:
    symbols: list[str]
    source_counts: dict[str, int]
    generated_at: datetime


class DynamicUniverseService:
    _FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
    _FMP_BASE_URL = "https://financialmodelingprep.com/stable"
    _MASSIVE_BASE_URL = "https://api.massive.com"

    def __init__(self) -> None:
        self._cached_snapshot: UniverseSnapshot | None = None

    def get_equity_symbols(self) -> UniverseSnapshot:
        now = datetime.now(tz=timezone.utc)
        refresh_seconds = max(60, int(settings.dynamic_universe_refresh_seconds or 3600))
        if self._cached_snapshot and (now - self._cached_snapshot.generated_at) < timedelta(seconds=refresh_seconds):
            return self._cached_snapshot

        source_order = [item.strip().lower() for item in settings.dynamic_universe_sources.split(",") if item.strip()]
        max_symbols = max(25, int(settings.dynamic_universe_max_symbols or 180))

        aggregate: list[str] = []
        source_counts: dict[str, int] = {}
        for source in source_order:
            discovered: list[str] = []
            try:
                if source == "finnhub":
                    discovered = self._from_finnhub(limit=max_symbols)
                elif source == "fmp":
                    discovered = self._from_fmp(limit=max_symbols)
                elif source == "massive":
                    discovered = self._from_massive(limit=max_symbols)
                elif source == "static":
                    discovered = self._static_seed_symbols()
            except Exception as exc:
                logger.warning("dynamic_universe_source_failed source=%s error=%s", source, exc)
                discovered = []

            if not discovered:
                continue

            source_counts[source] = len(discovered)
            aggregate.extend(discovered)
            if len(self._dedupe(aggregate)) >= max_symbols:
                break

        deduped = self._dedupe(aggregate)
        if len(deduped) < 10:
            # Always fail-safe to a known tradable seed set.
            deduped = self._static_seed_symbols()[:max_symbols]
            source_counts = {"static": len(deduped)}

        snapshot = UniverseSnapshot(
            symbols=deduped[:max_symbols],
            source_counts=source_counts,
            generated_at=now,
        )
        self._cached_snapshot = snapshot
        return snapshot

    def _from_finnhub(self, *, limit: int) -> list[str]:
        api_key = str(settings.finnhub_api_key or "").strip()
        if not api_key:
            return []

        params = {
            "exchange": "US",
            "token": api_key,
        }
        with httpx.Client(timeout=20) as client:
            response = client.get(
                f"{self._FINNHUB_BASE_URL}/stock/symbol",
                params=params,
                headers={"Accept": "application/json"},
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []

        picked: list[str] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            symbol = str(row.get("symbol") or "").upper().strip()
            symbol_type = str(row.get("type") or "").lower().strip()
            if symbol_type and "stock" not in symbol_type and "common" not in symbol_type:
                continue
            if not self._is_eligible_symbol(symbol):
                continue
            picked.append(symbol)
            if len(picked) >= limit:
                break
        return self._dedupe(picked)

    def _from_fmp(self, *, limit: int) -> list[str]:
        api_key = str(settings.fmp_api_key or "").strip()
        if not api_key:
            return []

        with httpx.Client(timeout=20) as client:
            response = client.get(
                f"{self._FMP_BASE_URL}/stock-list",
                params={"apikey": api_key},
                headers={"Accept": "application/json"},
            )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            return []

        picked: list[str] = []
        for row in payload:
            if not isinstance(row, dict):
                continue
            exchange_short = str(row.get("exchangeShortName") or "").upper().strip()
            if exchange_short and exchange_short not in {"NASDAQ", "NYSE", "AMEX"}:
                continue
            symbol = str(row.get("symbol") or "").upper().strip()
            if not self._is_eligible_symbol(symbol):
                continue
            picked.append(symbol)
            if len(picked) >= limit:
                break
        return self._dedupe(picked)

    def _from_massive(self, *, limit: int) -> list[str]:
        api_key = str(settings.massive_api_key or "").strip()
        if not api_key:
            return []

        params: dict[str, str | int] = {
            "market": "stocks",
            "active": "true",
            "locale": "us",
            "limit": min(max(limit, 25), 1000),
            "apiKey": api_key,
        }

        with httpx.Client(timeout=20) as client:
            response = client.get(
                f"{self._MASSIVE_BASE_URL}/v3/reference/tickers",
                params=params,
                headers={"Accept": "application/json"},
            )
        response.raise_for_status()
        payload = response.json()

        results = payload.get("results", []) if isinstance(payload, dict) else []
        picked: list[str] = []
        for row in results:
            if not isinstance(row, dict):
                continue
            ticker = str(row.get("ticker") or "").upper().strip()
            if not self._is_eligible_symbol(ticker):
                continue
            picked.append(ticker)
            if len(picked) >= limit:
                break
        return self._dedupe(picked)

    def _is_eligible_symbol(self, symbol: str) -> bool:
        if not symbol or len(symbol) > 5:
            return False
        if not _SYMBOL_RE.match(symbol):
            return False
        return True

    def _static_seed_symbols(self) -> list[str]:
        # Known liquid names used as deterministic fallback.
        return [
            "AAPL",
            "MSFT",
            "NVDA",
            "AMZN",
            "GOOGL",
            "META",
            "TSLA",
            "AVGO",
            "AMD",
            "QCOM",
            "JPM",
            "BAC",
            "GS",
            "V",
            "MA",
            "UNH",
            "LLY",
            "JNJ",
            "XOM",
            "CVX",
            "BA",
            "GE",
            "CAT",
            "WMT",
            "COST",
            "KO",
            "PEP",
            "NFLX",
            "DIS",
            "SPY",
            "QQQ",
            "IWM",
            "XLF",
            "XLK",
            "XLE",
            "XLV",
            "SMH",
            "SOXX",
            "TLT",
            "HYG",
        ]

    def _dedupe(self, symbols: list[str]) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for symbol in symbols:
            upper = symbol.upper().strip()
            if upper in seen:
                continue
            seen.add(upper)
            out.append(upper)
        return out


dynamic_universe_service = DynamicUniverseService()
