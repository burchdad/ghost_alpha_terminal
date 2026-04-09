from __future__ import annotations

from sqlalchemy.exc import OperationalError

from app.db.base import Base, engine
from app.db import models  # noqa: F401


def initialize_database() -> None:
    try:
        Base.metadata.create_all(bind=engine)
    except OperationalError as exc:
        # SQLite + multi-worker startup can race on CREATE TABLE.
        # Ignore "already exists" so startup can continue.
        if "already exists" in str(exc).lower():
            return
        raise
