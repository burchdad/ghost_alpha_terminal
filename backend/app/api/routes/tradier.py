from __future__ import annotations

from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.api.deps.auth import HighTrustUser
from app.core.config import settings
from app.db.models import User
from app.models.schemas import TradierOptionOrderRequest, TradierStrategyOrderRequest
from app.services.options_execution_service import options_execution_service
from app.services.tradier_client import tradier_client
from app.services.tradier_order_sync_service import tradier_order_sync_service

router = APIRouter(prefix="/tradier", tags=["tradier"])


class TradierOrderRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    side: Literal["buy", "sell"]
    qty: float = Field(gt=0)
    order_type: Literal["market", "limit"] = "market"
    time_in_force: Literal["day", "gtc"] = "day"
    limit_price: float | None = Field(default=None, gt=0)


def _raise_tradier_error(err: httpx.HTTPStatusError) -> None:
    detail: str
    try:
        detail = err.response.text or str(err)
    except Exception:
        detail = str(err)
    raise HTTPException(status_code=err.response.status_code, detail=detail)


@router.get("/config-check", summary="Safe Tradier configuration diagnostics")
def tradier_config_check() -> dict:
    return {
        "tradier_sandbox_api_key_present": bool(settings.tradier_sandbox_api_key),
        "tradier_sandbox_account_number_present": bool(settings.tradier_sandbox_account_number),
        "tradier_live_api_key_present": bool(settings.tradier_live_api_key),
        "tradier_live_account_number_present": bool(settings.tradier_live_account_number),
        "tradier_active_api_key_present": bool(settings.tradier_effective_api_key),
        "tradier_active_account_number_present": bool(settings.tradier_effective_account_number),
        "tradier_sandbox": settings.tradier_sandbox,
        "tradier_live_trading_enabled": settings.tradier_live_trading_enabled,
        "tradier_base_url": tradier_client.base_url,
        "app_env": settings.app_env,
    }


@router.get("/account/balances", summary="Get Tradier account balances")
def get_account_balances(user: User = HighTrustUser) -> dict:
    del user
    if not tradier_client.is_configured():
        raise HTTPException(status_code=400, detail="Tradier active credentials are not configured for current TRADIER_SANDBOX mode")

    try:
        return tradier_client.get(f"/accounts/{settings.tradier_effective_account_number}/balances")
    except httpx.HTTPStatusError as err:
        _raise_tradier_error(err)


@router.get("/quotes/{symbol}", summary="Get Tradier quote for one symbol")
def get_quote(symbol: str, user: User = HighTrustUser) -> dict:
    del user
    if not tradier_client.is_configured():
        raise HTTPException(status_code=400, detail="Tradier active credentials are not configured for current TRADIER_SANDBOX mode")

    try:
        return tradier_client.get("/markets/quotes", params={"symbols": symbol.upper(), "greeks": "false"})
    except httpx.HTTPStatusError as err:
        _raise_tradier_error(err)


@router.post("/orders", summary="Submit a new order to Tradier")
def submit_order(payload: TradierOrderRequest, user: User = HighTrustUser) -> dict:
    del user
    if not tradier_client.is_configured():
        raise HTTPException(status_code=400, detail="Tradier active credentials are not configured for current TRADIER_SANDBOX mode")
    if not settings.tradier_live_trading_enabled:
        raise HTTPException(status_code=403, detail="Tradier live trading is disabled by configuration")

    body: dict[str, str] = {
        "class": "equity",
        "symbol": payload.symbol.upper(),
        "side": payload.side,
        "quantity": str(payload.qty),
        "type": payload.order_type,
        "duration": payload.time_in_force,
    }
    if payload.order_type == "limit":
        if payload.limit_price is None:
            raise HTTPException(status_code=422, detail="limit_price is required for limit orders")
        body["price"] = str(payload.limit_price)

    try:
        return tradier_client.post_form(
            f"/accounts/{settings.tradier_effective_account_number}/orders",
            data=body,
        )
    except httpx.HTTPStatusError as err:
        _raise_tradier_error(err)


@router.post("/options/orders", summary="Submit a new single-leg options order to Tradier")
def submit_option_order(payload: TradierOptionOrderRequest, user: User = HighTrustUser) -> dict:
    del user
    if not tradier_client.is_configured():
        raise HTTPException(status_code=400, detail="Tradier active credentials are not configured for current TRADIER_SANDBOX mode")
    if not settings.tradier_live_trading_enabled and not payload.preview:
        raise HTTPException(status_code=403, detail="Tradier live trading is disabled by configuration")

    try:
        return options_execution_service.submit_tradier_option_order(payload)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except httpx.HTTPStatusError as err:
        _raise_tradier_error(err)


@router.post("/options/strategy-orders", summary="Submit a multileg or combo options strategy order to Tradier")
def submit_strategy_order(payload: TradierStrategyOrderRequest, user: User = HighTrustUser) -> dict:
    del user
    if not tradier_client.is_configured():
        raise HTTPException(status_code=400, detail="Tradier active credentials are not configured for current TRADIER_SANDBOX mode")
    if not settings.tradier_live_trading_enabled and not payload.preview:
        raise HTTPException(status_code=403, detail="Tradier live trading is disabled by configuration")

    try:
        return options_execution_service.submit_tradier_strategy_order(payload)
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except httpx.HTTPStatusError as err:
        _raise_tradier_error(err)


# ---------------------------------------------------------------------------
# Live account state — positions, orders, execution confirmation
# ---------------------------------------------------------------------------

@router.get("/account/positions", summary="Get live Tradier account positions")
def get_positions(user: User = HighTrustUser) -> dict:
    """Fetch current open positions directly from Tradier (broker source of truth)."""
    del user
    if not tradier_client.is_configured():
        raise HTTPException(
            status_code=400,
            detail="Tradier active credentials are not configured for current TRADIER_SANDBOX mode",
        )
    try:
        return tradier_client.get(
            f"/accounts/{settings.tradier_effective_account_number}/positions"
        )
    except httpx.HTTPStatusError as err:
        _raise_tradier_error(err)


@router.get("/account/orders", summary="Get Tradier account orders")
def get_orders(user: User = HighTrustUser) -> dict:
    """Fetch all orders from Tradier including status.  Includes pending, filled, canceled."""
    del user
    if not tradier_client.is_configured():
        raise HTTPException(
            status_code=400,
            detail="Tradier active credentials are not configured for current TRADIER_SANDBOX mode",
        )
    try:
        return tradier_client.get(
            f"/accounts/{settings.tradier_effective_account_number}/orders",
            params={"includeTags": "true"},
        )
    except httpx.HTTPStatusError as err:
        _raise_tradier_error(err)


@router.get("/account/orders/{order_id}", summary="Get Tradier order status by ID")
def get_order_status(order_id: str, user: User = HighTrustUser) -> dict:
    """Fetch a single Tradier order by ID — used for execution confirmation polling."""
    del user
    if not tradier_client.is_configured():
        raise HTTPException(
            status_code=400,
            detail="Tradier active credentials are not configured for current TRADIER_SANDBOX mode",
        )
    try:
        return tradier_client.get(
            f"/accounts/{settings.tradier_effective_account_number}/orders/{order_id}"
        )
    except httpx.HTTPStatusError as err:
        _raise_tradier_error(err)


# ---------------------------------------------------------------------------
# Real-time sync service state (from the background poller)
# ---------------------------------------------------------------------------

@router.get("/sync/health", summary="TradierOrderSyncService health and last-sync times")
def sync_health() -> dict:
    """Return the health of the real-time Tradier order sync background loop."""
    return tradier_order_sync_service.health()


@router.get("/sync/orders", summary="Cached live order state from sync service")
def sync_orders(user: User = HighTrustUser) -> dict:
    """Return all orders tracked by the real-time sync service, including transition history."""
    del user
    return {"orders": tradier_order_sync_service.all_orders()}


@router.get("/sync/orders/open", summary="Open/pending orders from sync service")
def sync_open_orders(user: User = HighTrustUser) -> dict:
    """Return only open/pending orders currently in the sync service cache."""
    del user
    return {"orders": tradier_order_sync_service.open_orders()}


@router.get("/sync/orders/{order_id}", summary="Get a single order's sync state and transition log")
def sync_order_detail(order_id: str, user: User = HighTrustUser) -> dict:
    """Return the sync-service state for a specific order, including all status transitions."""
    del user
    result = tradier_order_sync_service.get_order(order_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Order {order_id} not found in sync cache")
    return result


@router.get("/sync/positions", summary="Cached live positions from sync service")
def sync_positions(user: User = HighTrustUser) -> dict:
    """Return the latest positions snapshot maintained by the real-time sync loop."""
    del user
    return {"positions": tradier_order_sync_service.positions()}


@router.post("/sync/force-refresh", summary="Force an immediate Tradier order+position poll")
def sync_force_refresh(user: User = HighTrustUser) -> dict:
    """Trigger a synchronous poll of Tradier orders and positions outside the normal loop."""
    del user
    if not tradier_client.is_configured():
        raise HTTPException(status_code=400, detail="Tradier not configured")
    return tradier_order_sync_service.force_refresh()

