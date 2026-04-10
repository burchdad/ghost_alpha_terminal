from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.api.deps.auth import CurrentUser
from app.db.models import User
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: str
    email: str


class AuthResponse(BaseModel):
    user: UserResponse


def _serialize_user(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), email=str(user.email))


@router.post("/signup", response_model=AuthResponse, summary="Create a user account and start a session")
def signup(payload: SignupRequest, request: Request, response: Response) -> AuthResponse:
    if "@" not in payload.email or len(payload.email.strip()) < 5:
        raise HTTPException(status_code=400, detail="A valid email is required")
    user = auth_service.create_user(email=payload.email, password=payload.password)
    auth_service.issue_login_cookie(response=response, user_id=str(user.id), request=request)
    return AuthResponse(user=_serialize_user(user))


@router.post("/login", response_model=AuthResponse, summary="Authenticate user and start a session")
def login(payload: LoginRequest, request: Request, response: Response) -> AuthResponse:
    if "@" not in payload.email or len(payload.email.strip()) < 5:
        raise HTTPException(status_code=400, detail="A valid email is required")
    user = auth_service.authenticate_user(email=payload.email, password=payload.password)
    auth_service.issue_login_cookie(response=response, user_id=str(user.id), request=request)
    return AuthResponse(user=_serialize_user(user))


@router.post("/logout", summary="Revoke current session and clear auth cookie")
def logout(request: Request, response: Response) -> dict:
    auth_service.revoke_current_session(request)
    auth_service.clear_login_cookie(response=response)
    return {"ok": True}


@router.get("/me", response_model=AuthResponse, summary="Current authenticated user")
def me(user: User = CurrentUser) -> AuthResponse:
    return AuthResponse(user=_serialize_user(user))


@router.get("/alpaca/callback", summary="OAuth callback compatibility route")
def alpaca_callback_compat(code: str, state: str) -> RedirectResponse:
    qs = urlencode({"code": code, "state": state})
    return RedirectResponse(url=f"/alpaca/oauth/callback?{qs}", status_code=307)
