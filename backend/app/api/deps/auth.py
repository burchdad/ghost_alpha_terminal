from __future__ import annotations

from fastapi import Depends, Request

from app.db.models import User
from app.services.auth_service import auth_service


def require_current_user(request: Request) -> User:
    return auth_service.get_current_user(request)


CurrentUser = Depends(require_current_user)
