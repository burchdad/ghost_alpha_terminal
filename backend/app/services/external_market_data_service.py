from __future__ import annotations

from datetime import datetime, timezone

import httpx

from app.core.config import settings


class ExternalMarketDataService:
    """Fallback market data loader using Massive, Finnhub, and FMP."""

    _MASSIVE_BASE_URL = "https://api.massive.com"
    _FINNHUB_BASE_URL = "https://finnhub.io/api/v1"
    _FMP_BASE_URL = "https://financialmodelingprep.com/stable"

    def get_candles(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        start_utc = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
        end_utc = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
        if end_utc <= start_utc:
            return []

        rows = self._get_massive_candles(symbol=symbol, timeframe=timeframe, start=start_utc, end=end_utc)
        if rows:
            return rows

        rows = self._get_finnhub_candles(symbol=symbol, timeframe=timeframe, start=start_utc, end=end_utc)
        if rows:
            return rows

        return self._get_fmp_candles(symbol=symbol, timeframe=timeframe, start=start_utc, end=end_utc)

    def _get_massive_candles(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        api_key = str(settings.massive_api_key or "").strip()
        if not api_key:
            return []

        range_args = self._massive_range_params(timeframe)
        ticker = self._massive_ticker(symbol)
        if range_args is None or not ticker:
            return []

        multiplier, timespan = range_args
        from_date = start.date().isoformat()
        to_date = end.date().isoformat()
        params = {
            "adjusted": "true",
            "sort": "asc",
            "limit": 50000,
            "apiKey": api_key,
        }

        try:
            with httpx.Client(timeout=20) as client:
                response = client.get(
                    f"{self._MASSIVE_BASE_URL}/v2/aggs/ticker/{ticker}/range/{multiplier}/{timespan}/{from_date}/{to_date}",
                    params=params,
                    headers={"Accept": "application/json"},
                )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        results = payload.get("results", []) if isinstance(payload, dict) else []
        rows: list[dict] = []
        for item in results:
            if not isinstance(item, dict):
                continue
            ts = item.get("t")
            if ts is None:
                continue
            rows.append(
                {
                    "timestamp": datetime.fromtimestamp(float(ts) / 1000.0, tz=timezone.utc).isoformat(),
                    "open": item.get("o"),
                    "high": item.get("h"),
                    "low": item.get("l"),
                    "close": item.get("c"),
                    "volume": item.get("v") or 0,
                }
            )
        return rows

    def _get_finnhub_candles(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        api_key = str(settings.finnhub_api_key or "").strip()
        if not api_key or self._is_crypto_symbol(symbol):
            return []

        resolution = self._finnhub_resolution(timeframe)
        if not resolution:
            return []

        params = {
            "symbol": symbol.upper().strip(),
            "resolution": resolution,
            "from": int(start.timestamp()),
            "to": int(end.timestamp()),
            "token": api_key,
        }

        try:
            with httpx.Client(timeout=20) as client:
                response = client.get(
                    f"{self._FINNHUB_BASE_URL}/stock/candle",
                    params=params,
                    headers={"Accept": "application/json"},
                )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        if not isinstance(payload, dict) or payload.get("s") != "ok":
            return []

        opens = payload.get("o") or []
        highs = payload.get("h") or []
        lows = payload.get("l") or []
        closes = payload.get("c") or []
        volumes = payload.get("v") or []
        timestamps = payload.get("t") or []

        size = min(len(opens), len(highs), len(lows), len(closes), len(volumes), len(timestamps))
        rows: list[dict] = []
        for idx in range(size):
            ts = timestamps[idx]
            rows.append(
                {
                    "timestamp": datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat(),
                    "open": opens[idx],
                    "high": highs[idx],
                    "low": lows[idx],
                    "close": closes[idx],
                    "volume": volumes[idx] or 0,
                }
            )
        return rows

    def _get_fmp_candles(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        # FMP quickstart endpoint below is eod-oriented; keep this as daily fallback.
        if timeframe != "1d":
            return []

        api_key = str(settings.fmp_api_key or "").strip()
        if not api_key:
            return []

        params = {
            "symbol": symbol.upper().strip(),
            "from": start.date().isoformat(),
            "to": end.date().isoformat(),
            "apikey": api_key,
        }

        try:
            with httpx.Client(timeout=20) as client:
                response = client.get(
                    f"{self._FMP_BASE_URL}/historical-price-eod/full",
                    params=params,
                    headers={"Accept": "application/json"},
                )
            response.raise_for_status()
            payload = response.json()
        except Exception:
            return []

        records: list[dict] = []
        if isinstance(payload, list):
            records = [item for item in payload if isinstance(item, dict)]
        elif isinstance(payload, dict):
            inner = payload.get("historical")
            if isinstance(inner, list):
                records = [item for item in inner if isinstance(item, dict)]

        rows: list[dict] = []
        for item in records:
            date_text = str(item.get("date") or "").strip()
            if not date_text:
                continue
            rows.append(
                {
                    "timestamp": f"{date_text}T00:00:00+00:00",
                    "open": item.get("open"),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "close": item.get("close"),
                    "volume": item.get("volume") or 0,
                }
            )

        # Ensure ascending order for downstream indicators.
        return sorted(rows, key=lambda row: str(row.get("timestamp") or ""))

    def _massive_range_params(self, timeframe: str) -> tuple[int, str] | None:
        mapping: dict[str, tuple[int, str]] = {
            "1m": (1, "minute"),
            "5m": (5, "minute"),
            "15m": (15, "minute"),
            "1h": (1, "hour"),
            "4h": (4, "hour"),
            "1d": (1, "day"),
        }
        return mapping.get(timeframe)

    def _finnhub_resolution(self, timeframe: str) -> str | None:
        mapping: dict[str, str] = {
            "1m": "1",
            "5m": "5",
            "15m": "15",
            "1h": "60",
            "1d": "D",
        }
        return mapping.get(timeframe)

    def _is_crypto_symbol(self, symbol: str) -> bool:
        upper = symbol.upper().strip()
        return ("-" in upper and upper.endswith("-USD")) or (upper.endswith("USD") and len(upper) <= 12)

    def _massive_ticker(self, symbol: str) -> str:
        upper = symbol.upper().strip()
        if self._is_crypto_symbol(upper):
            normalized = upper.replace("-", "")
            return f"X:{normalized}"
        return upper


external_market_data_service = ExternalMarketDataService()
