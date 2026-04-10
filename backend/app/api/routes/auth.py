from __future__ import annotations

from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field

from app.api.deps.auth import CurrentUser
from app.db.models import User
from app.services.auth_service import auth_service
import secrets
import base64
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from app.db.models import User2FASetup
from app.db.session import get_session

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


class Verify2FASetupRequest(BaseModel):
    email: str
    twoFAMethod: str
    verificationCode: str


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


def _generate_totp_secret() -> str:
    """Generate a TOTP secret (base32 encoded random bytes)"""
    return base64.b32encode(secrets.token_bytes(20)).decode('utf-8')


def _generate_verification_code() -> str:
    """Generate a 6-digit verification code"""
    return str(secrets.randbelow(1000000)).zfill(6)


def _generate_totp_qr_code(email: str, secret: str) -> str:
    """Generate QR code URL for TOTP (placeholder - real implementation would use qrcode lib)"""
    issuer = "Ghost Alpha Terminal"
    label = f"{issuer} ({email})"
    params = {
        "secret": secret,
        "issuer": issuer,
        "algorithm": "SHA1",
        "digits": 6,
        "period": 30,
    }
    from urllib.parse import urlencode as encode
    qs = encode(params)
    return f"otpauth://totp/{label}?{qs}"

@router.post("/signup", response_model=AuthResponse, summary="Create a user account and start a session")
def signup(payload: SignupRequest, request: Request, response: Response) -> AuthResponse:
    if "@" not in payload.email or len(payload.email.strip()) < 5:
        raise HTTPException(status_code=400, detail="A valid email is required")
    user = auth_service.create_user(email=payload.email, password=payload.password)
    auth_service.issue_login_cookie(response=response, user_id=str(user.id), request=request)
    return AuthResponse(user=_serialize_user(user))


@router.post("/initiate-2fa", summary="Initiate 2FA setup during signup")
def initiate_2fa(payload: Initiate2FARequest, request: Request, response: Response) -> dict:
    """Initialize 2FA setup and create temporary record"""
    email = auth_service._normalize_email(payload.email)
    if "@" not in email or len(email) < 5:
        raise HTTPException(status_code=400, detail="Valid email required")

    with get_session() as session:
        # Check if email already registered
        existing = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if existing is not None:
            raise HTTPException(status_code=409, detail="Email already registered")

        # Delete any existing pending 2FA attempts
        session.query(User2FASetup).filter(User2FASetup.email == email).delete()

        now = datetime.now(tz=timezone.utc)
        expires_at = now + timedelta(minutes=15)  # 15 minute expiration

        if payload.twoFAMethod == "totp":
            secret = _generate_totp_secret()
            qr_code_url = _generate_totp_qr_code(email, secret)
        elif payload.twoFAMethod == "sms":
            secret = payload.phone_number if hasattr(payload, 'phone_number') else "SMS"
            qr_code_url = None
        else:  # email
            secret = email
            qr_code_url = None

        # Create temporary 2FA record
        record = User2FASetup(
            email=email,
            twoFAMethod=payload.twoFAMethod,
            twoFASecret=secret,
            verificationCode=_generate_verification_code(),
            verified=False,
            created_at=now,
            expires_at=expires_at,
        )
        session.add(record)
        session.flush()

        return {
            "success": True,
            "method": payload.twoFAMethod,
            "secret": secret if payload.twoFAMethod == "totp" else None,
            "qr_code": qr_code_url,
        }


@router.post("/verify-2fa-setup", summary="Verify 2FA code during signup")
def verify_2fa_setup(payload: Verify2FASetupRequest) -> dict:
    """Verify 2FA setup code"""
    email = auth_service._normalize_email(payload.email)

    with get_session() as session:
        record = session.execute(
            select(User2FASetup)
            .where(User2FASetup.email == email)
            .where(User2FASetup.twoFAMethod == payload.twoFAMethod)
        ).scalar_one_or_none()

        if record is None:
            raise HTTPException(status_code=404, detail="2FA setup not found")

        now = datetime.now(tz=timezone.utc)
        if record.expires_at < now:
            raise HTTPException(status_code=410, detail="2FA setup expired")

        # In production, verify actual TOTP/SMS/email code
        # For now, check against the code we generated
        if payload.verificationCode != record.verificationCode:
            raise HTTPException(status_code=400, detail="Invalid verification code")

        record.verified = True

    return {"success": True, "message": "2FA verified"}


@router.post("/signup-complete", response_model=AuthResponse, summary="Complete account creation")
def signup_complete(payload: SignupCompleteRequest, request: Request, response: Response) -> AuthResponse:
    """Complete account creation after 2FA verification"""
    email = auth_service._normalize_email(payload.email)

    if not payload.agreePrivacy or not payload.agreeTerms or not payload.agreeRisk:
        raise HTTPException(status_code=400, detail="All agreements must be accepted")

    with get_session() as session:
        # Verify 2FA was completed
        twofa_record = session.execute(
            select(User2FASetup)
            .where(User2FASetup.email == email)
            .where(User2FASetup.twoFAMethod == payload.twoFAMethod)
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
            twofa_secret=twofa_record.twoFASecret,
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

        # Clean up temporary 2FA record
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
