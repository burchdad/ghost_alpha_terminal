from __future__ import annotations

from sqlalchemy import select

from app.db.models import BrokerOAuthConnection
from app.db.session import get_session

_OAUTH_PROVIDER = "alpaca"


class AlpacaOAuthService:
    def get_connection(self) -> BrokerOAuthConnection | None:
        with get_session() as session:
            return session.execute(
                select(BrokerOAuthConnection).where(BrokerOAuthConnection.provider == _OAUTH_PROVIDER)
            ).scalar_one_or_none()

    def get_access_token(self) -> str | None:
        connection = self.get_connection()
        if not connection or not connection.connected or not connection.access_token:
            return None
        return connection.access_token

    def is_connected(self) -> bool:
        return bool(self.get_access_token())


alpaca_oauth_service = AlpacaOAuthService()
