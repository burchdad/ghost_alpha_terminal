from __future__ import annotations

from sqlalchemy import select

from app.db.models import BrokerOAuthConnection
from app.db.session import get_session

_OAUTH_PROVIDER = "alpaca"


class AlpacaOAuthService:
    def get_connection(self, *, user_id: str | None = None) -> BrokerOAuthConnection | None:
        with get_session() as session:
            if user_id:
                return session.execute(
                    select(BrokerOAuthConnection).where(
                        BrokerOAuthConnection.provider == _OAUTH_PROVIDER,
                        BrokerOAuthConnection.user_id == user_id,
                    )
                ).scalar_one_or_none()

            # Backward-compatible aggregate status for endpoints without user context.
            return session.execute(
                select(BrokerOAuthConnection)
                .where(BrokerOAuthConnection.provider == _OAUTH_PROVIDER, BrokerOAuthConnection.connected.is_(True))
                .order_by(BrokerOAuthConnection.updated_at.desc())
            ).scalars().first()

    def get_access_token(self, *, user_id: str | None = None) -> str | None:
        connection = self.get_connection(user_id=user_id)
        if not connection or not connection.connected or not connection.access_token:
            return None
        return connection.access_token

    def is_connected(self, *, user_id: str | None = None) -> bool:
        return bool(self.get_access_token(user_id=user_id))


alpaca_oauth_service = AlpacaOAuthService()
