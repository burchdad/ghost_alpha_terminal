import json
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException, Query

from app.models.schemas import (
    AlpacaAccountPnlResponse,
    AlpacaOrderRequest,
    AlpacaRequestIdEntry,
    AlpacaRequestIdsResponse,
)
from app.services.alpaca_client import alpaca_client
from app.core.config import settings
from app.services.request_id_store import request_id_store

router = APIRouter(prefix="/alpaca", tags=["alpaca"])


@router.get(
    "/request-ids",
    response_model=AlpacaRequestIdsResponse,
    summary="Recent Alpaca X-Request-ID values",
    description=(
        "Returns the most recent X-Request-ID header values captured from Alpaca "
        "API responses. Include these IDs when opening a support request with "
        "Alpaca so they can trace the call through their system."
    ),
)
def get_recent_request_ids(
    limit: int = Query(default=50, ge=1, le=100),
) -> AlpacaRequestIdsResponse:
    entries = request_id_store.get_recent(n=limit)
    return AlpacaRequestIdsResponse(
        recent=[
            AlpacaRequestIdEntry(
                alpaca_request_id=e.alpaca_request_id,
                endpoint=e.endpoint,
                method=e.method,
                status_code=e.status_code,
                timestamp=e.timestamp,
                symbol=e.symbol,
            )
            for e in reversed(entries)  # newest first
        ],
        total_captured=request_id_store.total_captured,
    )


def _raise_alpaca_error(err: httpx.HTTPStatusError) -> None:
    """Convert Alpaca HTTP errors to FastAPI HTTPException while preserving context."""
    detail: str
    try:
        payload = err.response.json()
        detail = json.dumps(payload)
    except Exception:
        detail = err.response.text or str(err)
    raise HTTPException(status_code=err.response.status_code, detail=detail)


@router.get("/account", summary="Get Alpaca account information")
def get_account() -> dict:
    try:
        return alpaca_client.get("/v2/account")
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.get("/config-check", summary="Safe Alpaca configuration diagnostics")
def alpaca_config_check() -> dict:
    """Return non-secret configuration status to quickly verify deployment wiring."""
    return {
        "alpaca_api_key_present": bool(settings.alpaca_api_key),
        "alpaca_secret_key_present": bool(settings.alpaca_secret_key),
        "alpaca_paper": settings.alpaca_paper,
        "alpaca_connect_client_id_present": bool(settings.alpaca_connect_client_id),
        "alpaca_connect_client_secret_present": bool(settings.alpaca_connect_client_secret),
        "alpaca_connect_redirect_uri": settings.alpaca_connect_redirect_uri,
        "app_env": settings.app_env,
    }


@router.get(
    "/account/pnl",
    response_model=AlpacaAccountPnlResponse,
    summary="Get account day gain/loss from equity vs last equity",
)
def get_account_pnl() -> AlpacaAccountPnlResponse:
    try:
        account = alpaca_client.get("/v2/account")
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)

    equity = float(account.get("equity", 0.0))
    last_equity = float(account.get("last_equity", 0.0))
    return AlpacaAccountPnlResponse(
        equity=equity,
        last_equity=last_equity,
        balance_change=round(equity - last_equity, 6),
    )


@router.get("/assets", summary="List assets from Alpaca")
def list_assets(
    status: Literal["active", "inactive"] = Query(default="active"),
    asset_class: Literal["us_equity", "crypto"] = Query(default="us_equity"),
) -> list[dict]:
    try:
        result = alpaca_client.get(
            "/v2/assets",
            params={"status": status, "asset_class": asset_class},
        )
        if isinstance(result, list):
            return result
        return [result]
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.get("/assets/{symbol}", summary="Get one asset by symbol")
def get_asset(symbol: str) -> dict:
    try:
        return alpaca_client.get(f"/v2/assets/{symbol.upper()}", symbol=symbol.upper())
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.post("/orders", summary="Submit a new order to Alpaca")
def submit_order(payload: AlpacaOrderRequest) -> dict:
    body = payload.model_dump(exclude_none=True)
    # qty or notional is required by Alpaca for order creation
    if "qty" not in body and "notional" not in body:
        raise HTTPException(status_code=422, detail="Either qty or notional must be provided")
    try:
        return alpaca_client.post("/v2/orders", body=body, symbol=payload.symbol.upper())
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.get("/orders", summary="List Alpaca orders")
def list_orders(
    status: str = Query(default="open"),
    limit: int = Query(default=50, ge=1, le=500),
    nested: bool = Query(default=True),
) -> list[dict]:
    try:
        result = alpaca_client.get(
            "/v2/orders",
            params={"status": status, "limit": limit, "nested": str(nested).lower()},
        )
        if isinstance(result, list):
            return result
        return [result]
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.get("/orders/by-client-id/{client_order_id}", summary="Get order by client_order_id")
def get_order_by_client_id(client_order_id: str) -> dict:
    try:
        return alpaca_client.get(
            "/v2/orders:by_client_order_id",
            params={"client_order_id": client_order_id},
        )
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.get("/positions", summary="List all open positions")
def list_positions() -> list[dict]:
    try:
        result = alpaca_client.get("/v2/positions")
        if isinstance(result, list):
            return result
        return [result]
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.get("/positions/{symbol}", summary="Get a position by symbol")
def get_position(symbol: str) -> dict:
    try:
        return alpaca_client.get(f"/v2/positions/{symbol.upper()}", symbol=symbol.upper())
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)
