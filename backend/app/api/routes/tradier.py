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
