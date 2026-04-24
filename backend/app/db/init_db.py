from __future__ import annotations

from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy import inspect, text

from app.db.base import Base, engine
from app.db import models  # noqa: F401


def _is_duplicate_column_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "already exists" in message or "duplicate column" in message


def _add_column_if_missing(*, conn, table_name: str, column_name: str, column_type: str, existing_columns: set[str]) -> None:
    if column_name in existing_columns:
        return
    try:
        conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"))
    except (OperationalError, ProgrammingError) as exc:
        if not _is_duplicate_column_error(exc):
            raise


def _apply_lightweight_migrations() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        if "broker_oauth_connections" in tables:
            broker_columns = {col["name"] for col in inspector.get_columns("broker_oauth_connections")}
            _add_column_if_missing(
                conn=conn,
                table_name="broker_oauth_connections",
                column_name="user_id",
                column_type="VARCHAR(36)",
                existing_columns=broker_columns,
            )

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
                "onboarding_completed": "BOOLEAN DEFAULT FALSE",
            }
            for column_name, column_type in user_column_specs.items():
                _add_column_if_missing(
                    conn=conn,
                    table_name="users",
                    column_name=column_name,
                    column_type=column_type,
                    existing_columns=user_columns,
                )

        if "user_2fa_setup" in tables:
            setup_columns = {col["name"] for col in inspector.get_columns("user_2fa_setup")}
            _add_column_if_missing(
                conn=conn,
                table_name="user_2fa_setup",
                column_name="verification_code_hash",
                column_type="VARCHAR(128)",
                existing_columns=setup_columns,
            )
            _add_column_if_missing(
                conn=conn,
                table_name="user_2fa_setup",
                column_name="failed_attempts",
                column_type="INTEGER DEFAULT 0",
                existing_columns=setup_columns,
            )
            _add_column_if_missing(
                conn=conn,
                table_name="user_2fa_setup",
                column_name="locked_until",
                column_type="TIMESTAMP",
                existing_columns=setup_columns,
            )

        if "user_sessions" in tables:
            session_columns = {col["name"] for col in inspector.get_columns("user_sessions")}
            session_column_specs = {
                "access_token_hash": "VARCHAR(128)",
                "device_fingerprint_hash": "VARCHAR(128)",
                "twofa_required": "BOOLEAN DEFAULT FALSE",
                "twofa_verified_at": "TIMESTAMP",
                "high_trust_expires_at": "TIMESTAMP",
                "twofa_challenge_method": "VARCHAR(32)",
                "twofa_challenge_code_hash": "VARCHAR(128)",
                "twofa_challenge_expires_at": "TIMESTAMP",
                "twofa_failed_attempts": "INTEGER DEFAULT 0",
                "twofa_locked_until": "TIMESTAMP",
                "risk_score": "INTEGER DEFAULT 0",
                "risk_reasons_json": "TEXT DEFAULT '[]'",
                "access_expires_at": "TIMESTAMP",
            }
            for column_name, column_type in session_column_specs.items():
                _add_column_if_missing(
                    conn=conn,
                    table_name="user_sessions",
                    column_name=column_name,
                    column_type=column_type,
                    existing_columns=session_columns,
                )

        if "password_reset_tokens" in tables:
            reset_columns = {col["name"] for col in inspector.get_columns("password_reset_tokens")}
            _add_column_if_missing(
                conn=conn,
                table_name="password_reset_tokens",
                column_name="failed_attempts",
                column_type="INTEGER DEFAULT 0",
                existing_columns=reset_columns,
            )
            _add_column_if_missing(
                conn=conn,
                table_name="password_reset_tokens",
                column_name="max_attempts",
                column_type="INTEGER DEFAULT 5",
                existing_columns=reset_columns,
            )


def initialize_database() -> None:
    try:
        Base.metadata.create_all(bind=engine)
        _apply_lightweight_migrations()
    except (OperationalError, ProgrammingError) as exc:
        # SQLite + multi-worker startup can race on CREATE TABLE.
        # Ignore duplicate-object errors here so startup can continue.
        if _is_duplicate_column_error(exc):
            return
        raise
