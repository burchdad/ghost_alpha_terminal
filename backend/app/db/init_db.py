from __future__ import annotations

from sqlalchemy.exc import OperationalError
from sqlalchemy import inspect, text

from app.db.base import Base, engine
from app.db import models  # noqa: F401


def _apply_lightweight_migrations() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "broker_oauth_connections" not in tables:
        return

    columns = {col["name"] for col in inspector.get_columns("broker_oauth_connections")}
    if "user_id" in columns:
        return

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE broker_oauth_connections ADD COLUMN user_id VARCHAR(36)"))


def initialize_database() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        _apply_lightweight_migrations()
    except OperationalError as exc:
        # SQLite + multi-worker startup can race on CREATE TABLE.
        # Ignore "already exists" so startup can continue.
        if "already exists" in str(exc).lower():
            return
        raise
