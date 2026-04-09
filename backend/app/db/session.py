from __future__ import annotations

from contextlib import contextmanager
from threading import Lock
from typing import Generator

from app.db.base import SessionLocal

_db_init_lock = Lock()
_db_initialized = False


def _ensure_db_initialized() -> None:
    global _db_initialized
    if _db_initialized:
        return
    with _db_init_lock:
        if _db_initialized:
            return
        from app.db.init_db import initialize_database

        initialize_database()
        _db_initialized = True


@contextmanager
def get_session() -> Generator:
    _ensure_db_initialized()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
