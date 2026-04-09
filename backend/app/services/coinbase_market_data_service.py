from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx


class CoinbaseMarketDataService:
    """Public Coinbase Exchange candle loader for crypto market data fallback."""

    _BASE_URL = "https://api.exchange.coinbase.com"

    def get_candles(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[dict]:
        product_id = self._to_product_id(symbol)
        granularity = self._granularity(timeframe)
        if not product_id or granularity is None:
            return []

        start_utc = start if start.tzinfo else start.replace(tzinfo=timezone.utc)
        end_utc = end if end.tzinfo else end.replace(tzinfo=timezone.utc)
        if end_utc <= start_utc:
            return []

        # Coinbase returns up to ~300 candles per request. Chunk long windows.
        max_points = 280
        window_seconds = granularity * max_points

        rows: list[dict] = []
        cursor = start_utc
        while cursor < end_utc:
            chunk_end = min(cursor + timedelta(seconds=window_seconds), end_utc)
            params = {
                "start": cursor.isoformat(),
                "end": chunk_end.isoformat(),
                "granularity": granularity,
            }
            try:
                with httpx.Client(timeout=20) as client:
                    response = client.get(
                        f"{self._BASE_URL}/products/{product_id}/candles",
                        params=params,
                        headers={"Accept": "application/json"},
                    )
                response.raise_for_status()
                payload = response.json()
            except Exception:
                cursor = chunk_end
                continue

            if isinstance(payload, list):
                for item in payload:
                    if not isinstance(item, list) or len(item) < 6:
                        continue
                    ts, low, high, open_, close, volume = item[:6]
                    rows.append(
                        {
                            "timestamp": datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat(),
                            "open": open_,
                            "high": high,
                            "low": low,
                            "close": close,
                            "volume": volume,
                        }
                    )

            cursor = chunk_end

        # Deduplicate by timestamp and return ascending order.
        dedup: dict[str, dict] = {}
        for row in rows:
            timestamp = str(row.get("timestamp") or "")
            if timestamp:
                dedup[timestamp] = row
        return [dedup[key] for key in sorted(dedup.keys())]

    def _to_product_id(self, symbol: str) -> str | None:
        upper = symbol.upper().strip()
        if "-" in upper:
            return upper
        if upper.endswith("USD") and len(upper) > 3:
            return f"{upper[:-3]}-USD"
        return None

    def _granularity(self, timeframe: str) -> int | None:
        mapping = {
            "1m": 60,
            "5m": 300,
            "15m": 900,
            "1h": 3600,
            "4h": 14400,
            "1d": 86400,
        }
        return mapping.get(timeframe)


coinbase_market_data_service = CoinbaseMarketDataService()
