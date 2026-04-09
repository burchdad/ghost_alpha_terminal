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

import httpx

from app.core.config import settings
from app.services.request_id_store import request_id_store

_PAPER_BASE = "https://paper-api.alpaca.markets"
_LIVE_BASE = "https://api.alpaca.markets"


class AlpacaClient:
    """Thin HTTP wrapper around the Alpaca REST API."""

    @property
    def _base_url(self) -> str:
        return _PAPER_BASE if settings.alpaca_paper else _LIVE_BASE

    def _headers(self) -> dict[str, str]:
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
    ) -> dict:
        """POST request to Alpaca. Raises httpx.HTTPStatusError on 4xx/5xx."""
        url = f"{self._base_url}{endpoint}"
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


alpaca_client = AlpacaClient()
