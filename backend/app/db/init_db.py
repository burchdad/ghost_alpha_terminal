from __future__ import annotations

from app.db.base import Base, engine
from app.db import models  # noqa: F401


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
