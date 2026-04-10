from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps.auth import CurrentUser
from app.core.config import settings
from app.db.models import User, User2FASetup
from app.db.session import get_session
from app.services.auth_service import auth_service
from app.services.twofa_service import twofa_service

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


class Initiate2FARequest(BaseModel):
    email: str
    twoFAMethod: str = Field(..., pattern="^(totp|sms|email)$")
    phoneNumber: str | None = None


class Verify2FASetupRequest(BaseModel):
    email: str
    twoFAMethod: str = Field(..., pattern="^(totp|sms|email)$")
    verificationCode: str


class Resend2FARequest(BaseModel):
    email: str
    twoFAMethod: str = Field(..., pattern="^(sms|email)$")
    phoneNumber: str | None = None


class SignupCompleteRequest(BaseModel):
    fullName: str
    email: str
    phoneNumber: str | None = None
    password: str = Field(min_length=8, max_length=128)
    twoFAMethod: str
    agreePrivacy: bool
    agreeTerms: bool
    agreeRisk: bool

def _serialize_user(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), email=str(user.email))


def _generate_verification_code() -> str:
    return str(secrets.randbelow(1000000)).zfill(6)

@router.post("/signup", response_model=AuthResponse, summary="Create a user account and start a session")
def signup(payload: SignupRequest, request: Request, response: Response) -> AuthResponse:
    raise HTTPException(
        status_code=410,
        detail="Legacy signup is disabled. Use /auth/initiate-2fa, /auth/verify-2fa-setup, and /auth/signup-complete.",
    )


@router.post("/initiate-2fa", summary="Initiate 2FA setup during signup")
def initiate_2fa(payload: Initiate2FARequest) -> dict:
    email = auth_service._normalize_email(payload.email)
    if "@" not in email or len(email) < 5:
        raise HTTPException(status_code=400, detail="Valid email required")

    method = payload.twoFAMethod
    now = datetime.now(tz=timezone.utc)
    expires_at = now + timedelta(minutes=settings.otp_code_ttl_minutes)

    with get_session() as session:
        existing = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Email already registered")

        session.query(User2FASetup).filter(User2FASetup.email == email).delete()
        secret: str
        code: str | None = None
        qr_code_url: str | None = None

        if method == "totp":
            secret = twofa_service.generate_totp_secret()
            qr_code_url = twofa_service.build_otpauth_uri(email=email, secret=secret)
        elif method == "sms":
            phone = (payload.phoneNumber or "").strip()
            if not phone:
                raise HTTPException(status_code=400, detail="Phone number is required for SMS 2FA")
            secret = phone
            code = _generate_verification_code()
            twofa_service.send_sms_code(phone_number=phone, code=code)
        else:
            secret = email
            code = _generate_verification_code()
            twofa_service.send_email_code(to_email=email, code=code)

        record = User2FASetup(
            email=email,
            twofa_method=method,
            twofa_secret=secret,
            verification_code=code,
            verified=False,
            created_at=now,
            expires_at=expires_at,
        )
        session.add(record)
        session.flush()

    return {
        "success": True,
        "method": method,
        "secret": secret if method == "totp" else None,
        "qr_code": qr_code_url,
        "expires_in_seconds": settings.otp_code_ttl_minutes * 60,
    }


@router.post("/resend-2fa-code", summary="Resend SMS or email verification code")
def resend_2fa_code(payload: Resend2FARequest) -> dict:
    email = auth_service._normalize_email(payload.email)
    method = payload.twoFAMethod
    now = datetime.now(tz=timezone.utc)

    with get_session() as session:
        record = session.execute(
            select(User2FASetup)
            .where(User2FASetup.email == email)
            .where(User2FASetup.twofa_method == method)
        ).scalar_one_or_none()

        if record is None:
            raise HTTPException(status_code=404, detail="2FA setup not found")
        if bool(record.verified):
            raise HTTPException(status_code=400, detail="2FA is already verified")

        code = _generate_verification_code()
        if method == "sms":
            phone = (payload.phoneNumber or record.twofa_secret or "").strip()
            if not phone:
                raise HTTPException(status_code=400, detail="Phone number is required for SMS 2FA")
            record.twofa_secret = phone
            twofa_service.send_sms_code(phone_number=phone, code=code)
        else:
            twofa_service.send_email_code(to_email=email, code=code)

        record.verification_code = code
        record.expires_at = now + timedelta(minutes=settings.otp_code_ttl_minutes)

    return {"success": True, "message": "Verification code sent"}


@router.post("/verify-2fa-setup", summary="Verify 2FA code during signup")
def verify_2fa_setup(payload: Verify2FASetupRequest) -> dict:
    email = auth_service._normalize_email(payload.email)
    method = payload.twoFAMethod
    raw_code = str(payload.verificationCode or "").strip()

    with get_session() as session:
        record = session.execute(
            select(User2FASetup)
            .where(User2FASetup.email == email)
            .where(User2FASetup.twofa_method == method)
        ).scalar_one_or_none()

        if record is None:
            raise HTTPException(status_code=404, detail="2FA setup not found")

        now = datetime.now(tz=timezone.utc)
        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise HTTPException(status_code=410, detail="2FA setup expired")

        if method == "totp":
            if not twofa_service.verify_totp(secret=record.twofa_secret, code=raw_code):
                raise HTTPException(status_code=400, detail="Invalid authenticator code")
        else:
            if not record.verification_code:
                raise HTTPException(status_code=400, detail="Verification code is not initialized")
            if raw_code != str(record.verification_code):
                raise HTTPException(status_code=400, detail="Invalid verification code")

        record.verified = True

    return {"success": True, "message": "2FA verified"}


@router.post("/signup-complete", response_model=AuthResponse, summary="Complete account creation")
def signup_complete(payload: SignupCompleteRequest, request: Request, response: Response) -> AuthResponse:
    email = auth_service._normalize_email(payload.email)

    if not payload.agreePrivacy or not payload.agreeTerms or not payload.agreeRisk:
        raise HTTPException(status_code=400, detail="All agreements must be accepted")

    with get_session() as session:
        existing = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Email already registered")

        twofa_record = session.execute(
            select(User2FASetup)
            .where(User2FASetup.email == email)
            .where(User2FASetup.twofa_method == payload.twoFAMethod)
        ).scalar_one_or_none()

        if twofa_record is None or not twofa_record.verified:
            raise HTTPException(status_code=400, detail="2FA verification required")

        now = datetime.now(tz=timezone.utc)

        # Create user
        user = User(
            email=email,
            password_hash=auth_service._hash_password(payload.password),
            full_name=payload.fullName,
            phone_number=payload.phoneNumber,
            twofa_method=payload.twoFAMethod,
            twofa_verified=True,
            twofa_secret=twofa_record.twofa_secret,
            privacy_policy_accepted=payload.agreePrivacy,
            terms_of_use_accepted=payload.agreeTerms,
            risk_disclosure_accepted=payload.agreeRisk,
            agreements_accepted_at=now,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        session.add(user)
        session.flush()
        session.query(User2FASetup).filter(User2FASetup.email == email).delete()

    # Issue session
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
