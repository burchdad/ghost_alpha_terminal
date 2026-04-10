from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps.auth import CurrentUser
from app.core.config import settings
from app.db.models import BrokerOAuthConnection, User
from app.db.session import get_session

router = APIRouter(prefix="/brokers", tags=["brokers"])


@router.get("/status", summary="Get broker connection status for the current user")
def broker_status(user: User = CurrentUser) -> dict:
    with get_session() as session:
        rows = session.execute(
            select(BrokerOAuthConnection).where(BrokerOAuthConnection.user_id == str(user.id))
        ).scalars().all()

    by_provider = {str(row.provider): row for row in rows}

    alpaca_row = by_provider.get("alpaca")
    alpaca_connected = bool(alpaca_row and alpaca_row.connected and alpaca_row.access_token)
    alpaca_accounts: list[str] = []
    if alpaca_connected:
        alpaca_accounts = ["paper" if settings.alpaca_paper else "live"]

    coinbase_keys_present = bool(settings.coinbase_api_key_name and settings.coinbase_api_private_key)

    return {
        "alpaca": {
            "connected": alpaca_connected,
            "accounts": alpaca_accounts,
        },
        "coinbase": {
            "connected": coinbase_keys_present,
            "accounts": ["live"] if coinbase_keys_present else [],
        },
        "tradier": {
            "connected": False,
            "accounts": [],
        },
    }
