"""
Alpaca HTTP client.

Wraps every call to the Alpaca Markets REST API and automatically
captures the X-Request-ID response header into the local
RequestIdStore so it can be referenced in support requests.

Configuration (via .env):
    ALPACA_API_KEY      — Alpaca API key ID
    ALPACA_SECRET_KEY   — Alpaca secret key
    ALPACA_PAPER        — True (default) → paper endpoint, False → live endpoint
"""
from __future__ import annotations

from datetime import datetime

import httpx

from app.core.config import settings
from app.services.alpaca_oauth_service import alpaca_oauth_service
from app.services.request_id_store import request_id_store

_PAPER_BASE = "https://paper-api.alpaca.markets"
_LIVE_BASE = "https://api.alpaca.markets"
_MARKET_DATA_STOCKS_BASE = "https://data.alpaca.markets/v2"
_MARKET_DATA_CRYPTO_BASE = "https://data.alpaca.markets/v1beta3/crypto/us"


class AlpacaClient:
    """Thin HTTP wrapper around the Alpaca REST API."""

    @property
    def _base_url(self) -> str:
        return _PAPER_BASE if settings.alpaca_paper else _LIVE_BASE

    def _headers(self, *, prefer_oauth: bool = True) -> dict[str, str]:
        access_token = alpaca_oauth_service.get_access_token() if prefer_oauth else None
        if access_token:
            return {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
        return {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
            "Content-Type": "application/json",
        }

    def _market_data_headers(self) -> dict[str, str]:
        return {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
            "Content-Type": "application/json",
        }

    def _record(
        self,
        response: httpx.Response,
        endpoint: str,
        method: str,
        symbol: str | None,
    ) -> None:
        request_id_store.record(
            alpaca_request_id=response.headers.get("x-request-id", ""),
            endpoint=endpoint,
            method=method,
            status_code=response.status_code,
            symbol=symbol,
        )

    def get(
        self,
        endpoint: str,
        *,
        symbol: str | None = None,
        params: dict | None = None,
    ) -> dict:
        """GET request to Alpaca. Raises httpx.HTTPStatusError on 4xx/5xx."""
        url = f"{self._base_url}{endpoint}"
        with httpx.Client(timeout=10) as client:
            resp = client.get(url, headers=self._headers(), params=params)
        self._record(resp, endpoint, "GET", symbol)
        resp.raise_for_status()
        return resp.json()

    def post(
        self,
        endpoint: str,
        body: dict,
        *,
        symbol: str | None = None,
        paper_override: bool | None = None,
    ) -> dict:
        """POST request to Alpaca. Raises httpx.HTTPStatusError on 4xx/5xx.

        paper_override: when provided, selects paper (True) or live (False)
        endpoint explicitly, ignoring the ALPACA_PAPER env var.
        """
        if paper_override is None:
            base = self._base_url
        else:
            base = _PAPER_BASE if paper_override else _LIVE_BASE
        url = f"{base}{endpoint}"
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, headers=self._headers(), json=body)
        self._record(resp, endpoint, "POST", symbol)
        resp.raise_for_status()
        return resp.json()

    def delete(
        self,
        endpoint: str,
        *,
        symbol: str | None = None,
    ) -> dict | None:
        """DELETE request to Alpaca. Returns None on 204 No Content."""
        url = f"{self._base_url}{endpoint}"
        with httpx.Client(timeout=10) as client:
            resp = client.delete(url, headers=self._headers())
        self._record(resp, endpoint, "DELETE", symbol)
        resp.raise_for_status()
        return resp.json() if resp.content else None

    def get_bars(
        self,
        *,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        limit: int | None = None,
    ) -> list[dict]:
        upper = symbol.upper()
        is_crypto = upper.endswith("USD") and len(upper) <= 12
        request_symbol = f"{upper[:-3]}/USD" if is_crypto else upper
        base_url = _MARKET_DATA_CRYPTO_BASE if is_crypto else _MARKET_DATA_STOCKS_BASE
        endpoint = "/bars" if is_crypto else "/stocks/bars"

        timeframe_map = {
            "1m": "1Min",
            "5m": "5Min",
            "15m": "15Min",
            "1h": "1Hour",
            "4h": "4Hour",
            "1d": "1Day",
        }
        params: dict[str, str | int] = {
            "symbols": request_symbol,
            "timeframe": timeframe_map.get(timeframe, "1Day"),
            "start": start.isoformat(),
            "end": end.isoformat(),
        }
        if limit is not None:
            params["limit"] = max(1, min(limit, 10000))

        with httpx.Client(timeout=20) as client:
            resp = client.get(f"{base_url}{endpoint}", headers=self._market_data_headers(), params=params)
        self._record(resp, endpoint, "GET", symbol)
        resp.raise_for_status()
        payload = resp.json()
        bars_map = payload.get("bars", {}) if isinstance(payload, dict) else {}
        rows = bars_map.get(request_symbol) or bars_map.get(upper) or []
        normalized: list[dict] = []
        for row in rows:
            normalized.append(
                {
                    "timestamp": row.get("t") or row.get("timestamp"),
                    "open": row.get("o") or row.get("open"),
                    "high": row.get("h") or row.get("high"),
                    "low": row.get("l") or row.get("low"),
                    "close": row.get("c") or row.get("close"),
                    "volume": row.get("v") or row.get("volume") or 0,
                }
            )
        return normalized

    def get_news(self, *, symbol: str, limit: int = 10) -> list[dict]:
        params = {
            "symbols": symbol.upper(),
            "limit": max(1, min(limit, 50)),
        }
        endpoint = "/v1beta1/news"
        with httpx.Client(timeout=20) as client:
            resp = client.get(
                f"https://data.alpaca.markets{endpoint}",
                headers=self._market_data_headers(),
                params=params,
            )
        self._record(resp, endpoint, "GET", symbol)
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("news", []) if isinstance(payload, dict) else []


alpaca_client = AlpacaClient()
