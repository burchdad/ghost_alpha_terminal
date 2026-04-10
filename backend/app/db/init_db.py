from __future__ import annotations

from sqlalchemy.exc import OperationalError
from sqlalchemy import inspect, text

from app.db.base import Base, engine
from app.db import models  # noqa: F401


def _apply_lightweight_migrations() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "broker_oauth_connections" in tables:
            broker_columns = {col["name"] for col in inspector.get_columns("broker_oauth_connections")}
            if "user_id" not in broker_columns:
                conn.execute(text("ALTER TABLE broker_oauth_connections ADD COLUMN user_id VARCHAR(36)"))

        if "users" in tables:
            user_columns = {col["name"] for col in inspector.get_columns("users")}
            user_column_specs = {
                "full_name": "VARCHAR(255)",
                "phone_number": "VARCHAR(32)",
                "twofa_method": "VARCHAR(32)",
                "twofa_verified": "BOOLEAN DEFAULT FALSE",
                "twofa_secret": "VARCHAR(255)",
                "privacy_policy_accepted": "BOOLEAN DEFAULT FALSE",
                "terms_of_use_accepted": "BOOLEAN DEFAULT FALSE",
                "risk_disclosure_accepted": "BOOLEAN DEFAULT FALSE",
                "agreements_accepted_at": "TIMESTAMP",
            }
            for column_name, column_type in user_column_specs.items():
                if column_name not in user_columns:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {column_name} {column_type}"))


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
