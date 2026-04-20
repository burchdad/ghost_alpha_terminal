"""
Charles Schwab API routes.

Exposes account, position, and order data from the connected Schwab OAuth account.
All endpoints require a high-trust session (re-authenticated within the step-up window).
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException

from app.api.deps.auth import HighTrustUser
from app.db.models import User
from app.services.schwab_client import schwab_client

router = APIRouter(prefix="/schwab", tags=["schwab"])


def _require_connected() -> None:
    if not schwab_client.is_connected():
        raise HTTPException(
            status_code=400,
            detail="No active Schwab OAuth connection. Connect via /auth/schwab/oauth/start.",
        )


@router.get("/status", summary="Schwab connection status")
def schwab_status() -> dict:
    """Return connection status and basic account metadata."""
    connected = schwab_client.is_connected()
    if not connected:
        return {"connected": False, "accounts": [], "error": "No active Schwab OAuth token"}

    try:
        accounts = schwab_client.list_accounts()
        summaries = []
        for acct in accounts:
            sec = acct.get("securitiesAccount", {})
            summaries.append(
                {
                    "account_hash": sec.get("accountNumber", ""),
                    "account_type": sec.get("type", ""),
                    "day_trader": sec.get("isDayTrader", False),
                    "closing_only_restricted": sec.get("isClosingOnlyRestricted", False),
                }
            )
        return {"connected": True, "account_count": len(accounts), "accounts": summaries}
    except Exception as exc:
        return {"connected": True, "accounts": [], "error": str(exc)}


@router.get("/accounts", summary="List all linked Schwab accounts")
def list_accounts(user: User = HighTrustUser) -> dict:
    """Return all linked Schwab accounts with balance and position fields."""
    del user
    _require_connected()
    try:
        accounts = schwab_client.list_accounts()
        return {"accounts": accounts, "count": len(accounts)}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/accounts/{account_hash}", summary="Get a specific Schwab account by encrypted hash")
def get_account(account_hash: str, user: User = HighTrustUser) -> dict:
    """Return full account detail (balances + positions) for a specific account hash."""
    del user
    _require_connected()
    try:
        return schwab_client.get_account(account_hash)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/accounts/{account_hash}/positions", summary="Get Schwab positions for an account")
def get_positions(account_hash: str, user: User = HighTrustUser) -> dict:
    """Return open positions from Schwab (broker source of truth)."""
    del user
    _require_connected()
    try:
        positions = schwab_client.get_positions(account_hash)
        return {"positions": positions, "count": len(positions), "account_hash": account_hash}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/accounts/{account_hash}/orders", summary="Get Schwab orders for an account")
def get_orders(
    account_hash: str,
    from_date: str | None = None,
    to_date: str | None = None,
    status: str | None = None,
    max_results: int = 100,
    user: User = HighTrustUser,
) -> dict:
    """Return orders from Schwab, optionally filtered by date range and status."""
    del user
    _require_connected()
    try:
        orders = schwab_client.get_orders(
            account_hash,
            from_date=from_date,
            to_date=to_date,
            status=status,
            max_results=max_results,
        )
        return {"orders": orders, "count": len(orders), "account_hash": account_hash}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/portfolio", summary="Normalised Schwab portfolio snapshot")
def portfolio_snapshot(user: User = HighTrustUser) -> dict:
    """Return a normalised portfolio snapshot from all linked Schwab accounts.

    This is the same data used internally by the portfolio service when Schwab
    is the active broker.
    """
    del user
    _require_connected()
    snap = schwab_client.portfolio_snapshot()
    if snap is None:
        raise HTTPException(status_code=503, detail="Schwab portfolio data unavailable")
    return snap
