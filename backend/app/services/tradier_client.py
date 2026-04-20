"""
Tradier HTTP client.

Provides a small wrapper for Tradier REST APIs using platform API-key mode.

Configuration (via .env):
    TRADIER_SANDBOX_API_KEY            - Tradier sandbox API token
    TRADIER_SANDBOX_ACCOUNT_NUMBER     - Tradier sandbox account number
    TRADIER_LIVE_API_KEY               - Tradier live API token
    TRADIER_LIVE_ACCOUNT_NUMBER        - Tradier live account number
    TRADIER_SANDBOX            - True uses sandbox endpoint, False uses live endpoint
    TRADIER_BASE_URL           - Optional explicit override for API host
"""
from __future__ import annotations

from typing import Any

import httpx

from app.core.config import settings

_SANDBOX_BASE = "https://sandbox.tradier.com/v1"
_LIVE_BASE = "https://api.tradier.com/v1"


class TradierClient:
    @property
    def base_url(self) -> str:
        if settings.tradier_base_url:
            return settings.tradier_base_url.rstrip("/")
        return _SANDBOX_BASE if settings.tradier_sandbox else _LIVE_BASE

    def is_configured(self) -> bool:
        return bool(settings.tradier_effective_api_key and settings.tradier_effective_account_number)

    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.tradier_effective_api_key}",
            "Accept": "application/json",
        }

    def get(self, endpoint: str, *, params: dict[str, Any] | None = None) -> dict:
        url = f"{self.base_url}{endpoint}"
        with httpx.Client(timeout=10) as client:
            response = client.get(url, headers=self.headers(), params=params)
        response.raise_for_status()
        return response.json()

    def post_form(self, endpoint: str, *, data: dict[str, Any]) -> dict:
        url = f"{self.base_url}{endpoint}"
        with httpx.Client(timeout=10) as client:
            response = client.post(url, headers=self.headers(), data=data)
        response.raise_for_status()
        return response.json()


tradier_client = TradierClient()
