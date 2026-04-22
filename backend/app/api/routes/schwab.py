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
from app.models.schemas import SchwabOrderRequest
from app.services.brokers.base import BrokerOrderRequest
from app.services.brokers.schwab_adapter import schwab_broker_adapter
from app.services.schwab_client import schwab_client

router = APIRouter(prefix="/schwab", tags=["schwab"])


def _require_connected(user_id: str) -> None:
    if not schwab_client.is_connected(user_id=user_id):
        raise HTTPException(
            status_code=400,
            detail="No active Schwab OAuth connection. Connect via /auth/schwab/oauth/start.",
        )


@router.get("/status", summary="Schwab connection status")
def schwab_status(user: User = HighTrustUser) -> dict:
    """Return connection status and basic account metadata."""
    connected = schwab_client.is_connected(user_id=str(user.id))
    if not connected:
        return {"connected": False, "accounts": [], "error": "No active Schwab OAuth token"}

    try:
        accounts = schwab_client.list_accounts(user_id=str(user.id))
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
    user_id = str(user.id)
    _require_connected(user_id)
    try:
        accounts = schwab_client.list_accounts(user_id=user_id)
        return {"accounts": accounts, "count": len(accounts)}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/accounts/{account_hash}", summary="Get a specific Schwab account by encrypted hash")
def get_account(account_hash: str, user: User = HighTrustUser) -> dict:
    """Return full account detail (balances + positions) for a specific account hash."""
    user_id = str(user.id)
    _require_connected(user_id)
    try:
        return schwab_client.get_account(account_hash, user_id=user_id)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=exc.response.status_code, detail=exc.response.text) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/accounts/{account_hash}/positions", summary="Get Schwab positions for an account")
def get_positions(account_hash: str, user: User = HighTrustUser) -> dict:
    """Return open positions from Schwab (broker source of truth)."""
    user_id = str(user.id)
    _require_connected(user_id)
    try:
        positions = schwab_client.get_positions(account_hash, user_id=user_id)
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
    user_id = str(user.id)
    _require_connected(user_id)
    try:
        orders = schwab_client.get_orders(
            account_hash,
            user_id=user_id,
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


@router.post("/orders", summary="Submit a new order to Schwab using the default connected account")
def submit_default_order(payload: SchwabOrderRequest, user: User = HighTrustUser) -> dict:
    user_id = str(user.id)
    _require_connected(user_id)
    broker_request = BrokerOrderRequest(
        symbol=payload.symbol.upper(),
        side="buy" if payload.side.startswith("buy") else "sell",
        qty=float(payload.quantity),
        asset_class=payload.asset_class,
        user_id=user_id,
        account_id=payload.account_hash,
        option_symbol=payload.symbol.upper() if payload.asset_class == "option" else None,
        option_side=payload.side if payload.asset_class == "option" else None,
        order_type=payload.order_type,
        time_in_force=payload.duration,
        limit_price=payload.limit_price,
        client_order_id=payload.client_order_id,
    )
    result = schwab_broker_adapter.submit_order(broker_request)
    if not result.submitted:
        raise HTTPException(status_code=400, detail=result.error or result.reason)
    return {"broker": result.broker, "order_id": result.order_id, "reason": result.reason, "raw": result.raw}


@router.post("/accounts/{account_hash}/orders", summary="Submit a new order to a specific Schwab account")
def submit_account_order(account_hash: str, payload: SchwabOrderRequest, user: User = HighTrustUser) -> dict:
    return submit_default_order(payload.model_copy(update={"account_hash": account_hash}), user=user)


@router.get("/portfolio", summary="Normalised Schwab portfolio snapshot")
def portfolio_snapshot(user: User = HighTrustUser) -> dict:
    """Return a normalised portfolio snapshot from all linked Schwab accounts.

    This is the same data used internally by the portfolio service when Schwab
    is the active broker.
    """
    user_id = str(user.id)
    _require_connected(user_id)
    snap = schwab_client.portfolio_snapshot(user_id=user_id)
    if snap is None:
        raise HTTPException(status_code=503, detail="Schwab portfolio data unavailable")
    return snap
