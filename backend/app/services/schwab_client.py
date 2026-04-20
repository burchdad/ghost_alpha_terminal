"""
Charles Schwab Trader API client.

Uses the per-user OAuth access token stored in BrokerOAuthConnection.
The Schwab Trader API (Individual Trader API) requires:
  - Base URL: https://api.schwabapi.com/trader/v1
  - Authorization: Bearer <access_token>

Key endpoints used:
  GET /accounts                          — list all linked accounts (returns encryptedAccountNumber)
  GET /accounts/{accountHash}            — account details (balances)
  GET /accounts/{accountHash}/positions  — open positions
  GET /accounts/{accountHash}/orders     — orders (optional params: fromEnteredTime, toEnteredTime, status)

Token refresh is attempted automatically when a 401 is received, using the
refresh_token stored alongside the access_token in BrokerOAuthConnection.
"""
from __future__ import annotations

import base64
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TRADER_BASE = "https://api.schwabapi.com/trader/v1"
_TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"

_PROVIDER = "schwab"


class SchwabClient:
    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    def _get_connection(self, user_id: str | None = None):
        """Return the most-recent connected Schwab BrokerOAuthConnection row."""
        from sqlalchemy import select

        from app.db.models import BrokerOAuthConnection
        from app.db.session import get_session

        with get_session() as session:
            q = select(BrokerOAuthConnection).where(
                BrokerOAuthConnection.provider == _PROVIDER,
                BrokerOAuthConnection.connected.is_(True),
            )
            if user_id:
                q = q.where(BrokerOAuthConnection.user_id == user_id)
            q = q.order_by(BrokerOAuthConnection.updated_at.desc())
            return session.execute(q).scalars().first()

    def _access_token(self, user_id: str | None = None) -> str | None:
        conn = self._get_connection(user_id=user_id)
        if not conn or not conn.access_token:
            return None
        return conn.access_token

    def _try_refresh(self, user_id: str | None = None) -> str | None:
        """Attempt to refresh the Schwab access token using the stored refresh_token."""
        from sqlalchemy import select

        from app.db.models import BrokerOAuthConnection
        from app.db.session import get_session

        conn = self._get_connection(user_id=user_id)
        if not conn or not conn.refresh_token:
            return None
        if not settings.schwab_client_id or not settings.schwab_client_secret:
            return None

        credentials = f"{settings.schwab_client_id}:{settings.schwab_client_secret}"
        encoded = base64.b64encode(credentials.encode()).decode()
        try:
            with httpx.Client(timeout=10) as client:
                resp = client.post(
                    _TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {encoded}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": conn.refresh_token,
                    },
                )
            resp.raise_for_status()
            token_data = resp.json()
            new_access = token_data.get("access_token")
            new_refresh = token_data.get("refresh_token", conn.refresh_token)
            if not new_access:
                return None

            # Persist updated tokens.
            with get_session() as session:
                row = session.execute(
                    select(BrokerOAuthConnection).where(BrokerOAuthConnection.id == conn.id)
                ).scalar_one_or_none()
                if row:
                    row.access_token = new_access
                    row.refresh_token = new_refresh
                    row.obtained_at = datetime.now(tz=timezone.utc)
                    row.updated_at = datetime.now(tz=timezone.utc)
                    row.last_error = None
                    session.commit()

            return new_access
        except Exception as exc:
            logger.warning("Schwab token refresh failed: %s", exc)
            return None

    def is_connected(self, user_id: str | None = None) -> bool:
        return bool(self._access_token(user_id=user_id))

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }

    def get(self, endpoint: str, *, params: dict[str, Any] | None = None, user_id: str | None = None) -> dict:
        token = self._access_token(user_id=user_id)
        if not token:
            raise RuntimeError("No connected Schwab account; token unavailable.")

        url = f"{_TRADER_BASE}{endpoint}"
        with httpx.Client(timeout=12) as client:
            resp = client.get(url, headers=self._headers(token), params=params)

        # Auto-refresh on 401 and retry once.
        if resp.status_code == 401:
            new_token = self._try_refresh(user_id=user_id)
            if new_token:
                with httpx.Client(timeout=12) as client:
                    resp = client.get(url, headers=self._headers(new_token), params=params)

        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Account helpers
    # ------------------------------------------------------------------

    def list_accounts(self, *, user_id: str | None = None) -> list[dict]:
        """Return all Schwab linked accounts (includes encryptedAccountNumber)."""
        try:
            payload = self.get("/accounts", params={"fields": "positions"}, user_id=user_id)
            if isinstance(payload, list):
                return payload
            return []
        except Exception as exc:
            logger.warning("Schwab list_accounts failed: %s", exc)
            return []

    def get_account(self, account_hash: str, *, user_id: str | None = None) -> dict:
        """Fetch full account detail (balances + positions) by encrypted hash."""
        return self.get(f"/accounts/{account_hash}", params={"fields": "positions"}, user_id=user_id)

    def get_positions(self, account_hash: str, *, user_id: str | None = None) -> list[dict]:
        """Return open positions for the given account hash."""
        try:
            payload = self.get(f"/accounts/{account_hash}", params={"fields": "positions"}, user_id=user_id)
            sec_acct = payload.get("securitiesAccount", {})
            return sec_acct.get("positions", []) or []
        except Exception as exc:
            logger.warning("Schwab get_positions failed for %s: %s", account_hash, exc)
            return []

    def get_orders(
        self,
        account_hash: str,
        *,
        user_id: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        status: str | None = None,
        max_results: int = 100,
    ) -> list[dict]:
        """Return orders for the given account hash."""
        params: dict[str, Any] = {"maxResults": max_results}
        if from_date:
            params["fromEnteredTime"] = from_date
        if to_date:
            params["toEnteredTime"] = to_date
        if status:
            params["status"] = status
        try:
            payload = self.get(f"/accounts/{account_hash}/orders", params=params, user_id=user_id)
            return payload if isinstance(payload, list) else []
        except Exception as exc:
            logger.warning("Schwab get_orders failed for %s: %s", account_hash, exc)
            return []

    # ------------------------------------------------------------------
    # Portfolio snapshot helper (used by live_portfolio_service)
    # ------------------------------------------------------------------

    def portfolio_snapshot(self, *, user_id: str | None = None) -> dict | None:
        """Return a normalised portfolio dict or None if not connected."""
        if not self.is_connected(user_id=user_id):
            return None

        accounts = self.list_accounts(user_id=user_id)
        if not accounts:
            return None

        total_equity = 0.0
        total_buying_power = 0.0
        all_positions: list[dict] = []
        account_labels: list[str] = []

        for acct in accounts:
            sec_acct = acct.get("securitiesAccount", {})
            if not sec_acct:
                continue
            acct_hash = sec_acct.get("accountNumber", "")
            acct_type = sec_acct.get("type", "CASH")
            initial_balances = sec_acct.get("initialBalances", {})
            current_balances = sec_acct.get("currentBalances", {})
            projected = sec_acct.get("projectedBalances", {})

            equity = float(
                current_balances.get("liquidationValue")
                or initial_balances.get("accountValue")
                or 0.0
            )
            buying_power = float(
                projected.get("cashAvailableForTrading")
                or current_balances.get("cashAvailableForTrading")
                or 0.0
            )
            total_equity += equity
            total_buying_power += buying_power
            account_labels.append(f"Schwab {acct_type} ...{acct_hash[-4:]}" if len(acct_hash) >= 4 else "Schwab")

            for pos in sec_acct.get("positions", []) or []:
                instrument = pos.get("instrument", {})
                symbol = str(instrument.get("symbol", "")).upper()
                if not symbol:
                    continue
                long_qty = float(pos.get("longQuantity") or 0.0)
                short_qty = float(pos.get("shortQuantity") or 0.0)
                qty = long_qty if long_qty > 0 else -short_qty
                avg_price = float(pos.get("averagePrice") or 0.0)
                market_value = float(pos.get("marketValue") or avg_price * abs(qty))
                current_price = float(pos.get("currentDayProfitLossPercentage") and avg_price or avg_price)
                # Schwab provides currentDayProfitLoss; use marketValue for total unrealised
                unrealized_pnl = float(pos.get("currentDayProfitLoss") or 0.0)
                cost_basis = avg_price * abs(qty)
                unrealized_pnl_pct = (unrealized_pnl / cost_basis) if cost_basis > 0 else 0.0
                side = "LONG" if qty > 0 else "SHORT"
                asset_type = str(instrument.get("assetType", "EQUITY"))
                all_positions.append({
                    "symbol": symbol,
                    "strategy": "LIVE_SCHWAB",
                    "side": side,
                    "entry_price": round(avg_price, 4),
                    "current_price": round(current_price, 4),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "unrealized_pnl_pct": round(unrealized_pnl_pct, 4),
                    "units": abs(qty),
                    "notional": round(market_value, 2),
                    "sector": self._sector_for_asset(symbol, asset_type),
                    "opened_at": datetime.now(tz=timezone.utc),
                    "source": "schwab",
                    "account_hash": acct_hash,
                })

        if total_equity == 0.0 and not all_positions:
            return None

        return {
            "account_balance": round(total_equity, 2),
            "buying_power": round(total_buying_power, 2),
            "positions": all_positions,
            "account_labels": account_labels,
            "account_count": len(accounts),
        }

    @staticmethod
    def _sector_for_asset(symbol: str, asset_type: str) -> str:
        if asset_type in {"OPTION", "FUTURE_OPTION"}:
            return "OPTIONS"
        if asset_type in {"FIXED_INCOME"}:
            return "BONDS"
        if asset_type in {"CASH_EQUIVALENT"}:
            return "CASH"
        mapping = {
            "AAPL": "TECH", "MSFT": "TECH", "NVDA": "TECH", "AMD": "TECH",
            "TSLA": "AUTO", "SPY": "INDEX", "QQQ": "INDEX", "IWM": "INDEX",
        }
        return mapping.get(symbol.upper(), "EQUITY")


schwab_client = SchwabClient()
