from __future__ import annotations

import base64
import re
import secrets
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from ecdsa import BadSignatureError, VerifyingKey, util as ecdsa_util
from ecdsa.keys import MalformedPointError
from sqlalchemy import select

from app.api.deps.auth import CurrentUser
from app.core.config import settings
from app.db.models import (
    AuthAuditLog,
    AuthRateLimitBucket,
    LoginSecurityState,
    PasswordResetToken,
    BrokerOAuthConnection,
    TrustedDevice,
    User,
    User2FASetup,
    UserSession,
    WebAuthnCredential,
)
from app.db.session import get_session
from app.services.auth_service import auth_service
from app.services.twofa_service import twofa_service

router = APIRouter(prefix="/auth", tags=["auth"])
_webauthn_challenges: dict[str, dict] = {}


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


class TwoFAChallengeRequest(BaseModel):
    fallbackMethod: str | None = Field(default=None, pattern="^(sms|email)$")
    phoneNumber: str | None = None


class TwoFAVerifyRequest(BaseModel):
    verificationCode: str
    trustDevice: bool = False
    deviceLabel: str | None = None


class WebAuthnChallengeRequest(BaseModel):
    deviceLabel: str | None = None


class WebAuthnRegisterChallengeRequest(BaseModel):
    deviceLabel: str | None = None


class WebAuthnRegisterRequest(BaseModel):
    challengeId: str = Field(min_length=8, max_length=128)
    credentialId: str = Field(min_length=8, max_length=1024)
    publicKeyPem: str = Field(min_length=32)
    algorithm: str = Field(default="ES256", min_length=3, max_length=32)
    signCount: int = Field(default=0, ge=0)
    transports: list[str] = []


class WebAuthnVerifyRequest(BaseModel):
    challengeId: str = Field(min_length=8, max_length=128)
    credentialId: str = Field(min_length=8, max_length=1024)
    clientDataJSON: str = Field(min_length=16)
    authenticatorData: str = Field(min_length=8)
    signature: str = Field(min_length=8)
    userHandle: str | None = None


class TrustedDeviceResponse(BaseModel):
    id: int
    label: str | None
    first_seen_at: str
    last_seen_at: str
    trusted_until: str
    last_ip_address: str | None


class ForgotPasswordRequest(BaseModel):
    email: str
    captchaToken: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    newPassword: str = Field(min_length=8, max_length=128)

def _serialize_user(user: User) -> UserResponse:
    return UserResponse(id=str(user.id), email=str(user.email))


def _generate_verification_code() -> str:
    return str(secrets.randbelow(1000000)).zfill(6)


def _hash_verification_code(code: str) -> str:
    secret = settings.auth_session_secret or "ghost-alpha-dev-otp-secret"
    return hmac.new(secret.encode("utf-8"), code.encode("utf-8"), hashlib.sha256).hexdigest()


def _hash_reset_token(token: str) -> str:
    # Token hashing prevents database disclosure from exposing active reset links.
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _hash_rate_key(scope: str, value: str) -> str:
    secret = settings.auth_session_secret or "ghost-alpha-dev-rate-limit-secret"
    raw = f"{scope}:{value}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), raw, hashlib.sha256).hexdigest()


def _write_auth_audit(
    *,
    event_type: str,
    status: str,
    request: Request,
    user: User | None = None,
    email: str | None = None,
    method: str | None = None,
    metadata: dict | None = None,
) -> None:
    now = datetime.now(tz=timezone.utc)
    metadata_json = json.dumps(metadata or {})
    ip_address = _extract_client_ip(request)
    device_fingerprint = auth_service._compute_device_fingerprint(request)
    with get_session() as session:
        session.add(
            AuthAuditLog(
                user_id=str(user.id) if user is not None else None,
                email=str(user.email) if user is not None else (email or None),
                event_type=event_type,
                status=status,
                method=method,
                ip_address=ip_address,
                user_agent=request.headers.get("user-agent"),
                device_fingerprint_hash=device_fingerprint,
                metadata_json=metadata_json,
                created_at=now,
            )
        )


def _get_login_state_key(email: str) -> str:
    return _hash_rate_key("login:email", auth_service._normalize_email(email))


def _load_login_security_state(email: str) -> LoginSecurityState | None:
    key_hash = _get_login_state_key(email)
    with get_session() as session:
        return session.execute(
            select(LoginSecurityState).where(LoginSecurityState.email_key_hash == key_hash)
        ).scalar_one_or_none()


def _record_login_failure(email: str, now: datetime) -> tuple[int, datetime | None]:
    key_hash = _get_login_state_key(email)
    window = timedelta(minutes=max(1, int(settings.login_failure_window_minutes)))
    with get_session() as session:
        state = session.execute(
            select(LoginSecurityState).where(LoginSecurityState.email_key_hash == key_hash)
        ).scalar_one_or_none()

        if state is None:
            state = LoginSecurityState(
                email_key_hash=key_hash,
                failed_attempts=1,
                first_failed_at=now,
                last_failed_at=now,
                locked_until=None,
                updated_at=now,
            )
            session.add(state)
            return (1, None)

        first_failed = state.first_failed_at if state.first_failed_at and state.first_failed_at.tzinfo else (
            state.first_failed_at.replace(tzinfo=timezone.utc) if state.first_failed_at else None
        )
        if first_failed is None or first_failed <= (now - window):
            state.failed_attempts = 1
            state.first_failed_at = now
            state.last_failed_at = now
            state.locked_until = None
            state.updated_at = now
            return (1, None)

        state.failed_attempts = int(state.failed_attempts or 0) + 1
        state.last_failed_at = now
        state.updated_at = now
        locked_until: datetime | None = None
        if state.failed_attempts >= max(1, int(settings.login_lock_after_failures)):
            locked_until = now + timedelta(minutes=max(1, int(settings.login_lock_minutes)))
            state.locked_until = locked_until
        return (int(state.failed_attempts), locked_until)


def _clear_login_failures(email: str) -> None:
    key_hash = _get_login_state_key(email)
    with get_session() as session:
        state = session.execute(
            select(LoginSecurityState).where(LoginSecurityState.email_key_hash == key_hash)
        ).scalar_one_or_none()
        if state is None:
            return
        state.failed_attempts = 0
        state.first_failed_at = None
        state.last_failed_at = None
        state.locked_until = None
        state.updated_at = datetime.now(tz=timezone.utc)


def _verify_code_hash(candidate: str, code_hash: str | None) -> bool:
    if not code_hash:
        return False
    return hmac.compare_digest(_hash_verification_code(candidate), str(code_hash))


def _is_locked(locked_until: datetime | None, now: datetime) -> bool:
    if locked_until is None:
        return False
    effective = locked_until if locked_until.tzinfo else locked_until.replace(tzinfo=timezone.utc)
    return effective > now


def _record_failed_attempt(record, now: datetime) -> None:
    record.failed_attempts = int(record.failed_attempts or 0) + 1
    max_attempts = max(1, int(settings.otp_max_attempts))
    if record.failed_attempts >= max_attempts:
        record.locked_until = now + timedelta(minutes=max(1, int(settings.otp_lockout_minutes)))


def _resolve_login_2fa_method(user: User, fallback_method: str | None = None) -> str:
    configured = str(user.twofa_method or "").strip().lower()
    if configured == "totp":
        return "totp"
    if configured in {"sms", "email"}:
        # TOTP is primary; weaker methods are allowed only when no TOTP is configured.
        return configured
    if fallback_method in {"sms", "email"}:
        return fallback_method
    return "email"


def _send_security_alert_for_request(*, user: User, method: str, request: Request, event: str) -> None:
    forwarded = request.headers.get("x-forwarded-for")
    ip_address = forwarded.split(",", 1)[0].strip() if forwarded else (request.client.host if request.client else None)
    device = request.headers.get("user-agent")
    location = request.headers.get("x-geo-country") or request.headers.get("x-geo-city")
    twofa_service.send_security_alert(
        to_email=str(user.email),
        method=method,
        ip_address=ip_address,
        device=device,
        location=location,
        event=event,
    )


def _normalize_phone_number(raw: str | None) -> str:
    candidate = str(raw or "").strip()
    if not candidate:
        return ""
    # Keep a single leading plus and strip common separators from user input.
    if candidate.startswith("+"):
        candidate = "+" + re.sub(r"[^0-9]", "", candidate[1:])
    else:
        candidate = re.sub(r"[^0-9]", "", candidate)
    if re.fullmatch(r"\+[1-9]\d{7,14}", candidate):
        return candidate
    return ""


def _extract_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        candidate = forwarded.split(",", 1)[0].strip()
        if candidate:
            return candidate
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _coerce_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _urlsafe_b64decode(data: str) -> bytes:
    padded = data + "=" * ((4 - len(data) % 4) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def _decode_webauthn_client_data(client_data_json_b64: str) -> tuple[dict, bytes]:
    decoded = _urlsafe_b64decode(client_data_json_b64)
    payload = json.loads(decoded.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Invalid clientDataJSON payload")
    return (payload, decoded)


def _decode_authenticator_data(authenticator_data_b64: str) -> tuple[bytes, int, int]:
    decoded = _urlsafe_b64decode(authenticator_data_b64)
    if len(decoded) < 37:
        raise ValueError("Invalid authenticatorData length")
    flags = int(decoded[32])
    sign_count = int.from_bytes(decoded[33:37], byteorder="big")
    return (decoded, flags, sign_count)


def _verify_webauthn_signature(*, public_key_pem: str, signature_b64: str, authenticator_data_raw: bytes, client_data_raw: bytes) -> None:
    digest = hashlib.sha256(client_data_raw).digest()
    signed_data = authenticator_data_raw + digest
    signature = _urlsafe_b64decode(signature_b64)
    try:
        verifying_key = VerifyingKey.from_pem(public_key_pem)
        verifying_key.verify(
            signature,
            signed_data,
            hashfunc=hashlib.sha256,
            sigdecode=ecdsa_util.sigdecode_der,
        )
    except (BadSignatureError, ValueError, MalformedPointError) as exc:
        raise ValueError("Invalid WebAuthn signature") from exc


def _purge_expired_webauthn_challenges(now: datetime) -> None:
    expired = [
        challenge_id
        for challenge_id, payload in _webauthn_challenges.items()
        if _coerce_utc(payload["expires_at"]) <= now
    ]
    for challenge_id in expired:
        _webauthn_challenges.pop(challenge_id, None)


def _consume_rate_limit(*, scope: str, key_value: str, now: datetime, max_attempts: int, window_minutes: int) -> tuple[int, bool]:
    key_hash = _hash_rate_key(scope, key_value)
    window = timedelta(minutes=max(1, int(window_minutes)))
    window_start = now - window
    with get_session() as session:
        bucket = session.execute(
            select(AuthRateLimitBucket)
            .where(AuthRateLimitBucket.scope == scope)
            .where(AuthRateLimitBucket.bucket_key_hash == key_hash)
        ).scalar_one_or_none()

        if bucket is None:
            bucket = AuthRateLimitBucket(
                scope=scope,
                bucket_key_hash=key_hash,
                window_start=now,
                attempts=1,
                blocked_until=None,
                created_at=now,
                updated_at=now,
            )
            session.add(bucket)
            return (1, False)

        blocked_until = _coerce_utc(bucket.blocked_until) if bucket.blocked_until else None
        if blocked_until and blocked_until > now:
            return (int(bucket.attempts or 0), True)

        bucket_window_start = _coerce_utc(bucket.window_start)
        if bucket_window_start <= window_start:
            bucket.window_start = now
            bucket.attempts = 1
            bucket.blocked_until = None
            bucket.updated_at = now
            return (1, False)

        bucket.attempts = int(bucket.attempts or 0) + 1
        bucket.updated_at = now
        if bucket.attempts > max(1, int(max_attempts)):
            bucket.blocked_until = now + window
            return (int(bucket.attempts), True)
        return (int(bucket.attempts), False)


def _requires_forgot_password_captcha(*, ip_attempts: int) -> bool:
    return ip_attempts >= max(1, int(settings.password_reset_captcha_after_attempts))


def _verify_turnstile_token(*, token: str, remote_ip: str) -> bool:
    if not settings.turnstile_secret_key:
        return False

    payload = urlencode(
        {
            "secret": settings.turnstile_secret_key,
            "response": token,
            "remoteip": remote_ip,
        }
    ).encode("utf-8")
    req = UrlRequest(
        url="https://challenges.cloudflare.com/turnstile/v0/siteverify",
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urlopen(req, timeout=8) as response:
            decoded = json.loads(response.read().decode("utf-8"))
            return bool(decoded.get("success"))
    except Exception:
        return False

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
            phone = _normalize_phone_number(payload.phoneNumber)
            if not phone:
                raise HTTPException(status_code=400, detail="Valid E.164 phone number is required for SMS 2FA")
            secret = phone
            # Twilio Verify manages the code — we don't generate or store one
            twofa_service.send_sms_verify(phone_number=phone)
        else:
            secret = email
            code = _generate_verification_code()
            twofa_service.send_email_code(to_email=email, code=code)

        record = User2FASetup(
            email=email,
            twofa_method=method,
            twofa_secret=secret,
            verification_code_hash=_hash_verification_code(code) if code else None,
            failed_attempts=0,
            locked_until=None,
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

        if method == "sms":
            phone = _normalize_phone_number(payload.phoneNumber or record.twofa_secret)
            if not phone:
                raise HTTPException(status_code=400, detail="Valid E.164 phone number is required for SMS 2FA")
            record.twofa_secret = phone
            twofa_service.send_sms_verify(phone_number=phone)
            # Twilio Verify manages the code; clear any stale stored code
            record.verification_code_hash = None
        else:
            code = _generate_verification_code()
            twofa_service.send_email_code(to_email=email, code=code)
            record.verification_code_hash = _hash_verification_code(code)

        record.expires_at = now + timedelta(minutes=settings.otp_code_ttl_minutes)
        record.failed_attempts = 0
        record.locked_until = None

    return {"success": True, "message": "Verification code sent"}


@router.post("/verify-2fa-setup", summary="Verify 2FA code during signup")
def verify_2fa_setup(payload: Verify2FASetupRequest) -> dict:
    email = auth_service._normalize_email(payload.email)
    method = payload.twoFAMethod
    raw_code = str(payload.verificationCode or "").strip()

    failure_detail: str | None = None

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
        if _is_locked(record.locked_until, now):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later")

        if method == "totp":
            if not twofa_service.verify_totp(secret=record.twofa_secret, code=raw_code):
                _record_failed_attempt(record, now)
                failure_detail = "Invalid authenticator code"
        elif method == "sms":
            # Twilio Verify owns the code — delegate check to their API
            phone = str(record.twofa_secret or "")
            if not twofa_service.verify_sms_code(phone_number=phone, code=raw_code):
                _record_failed_attempt(record, now)
                failure_detail = "Invalid or expired SMS code"
        else:
            if not record.verification_code_hash:
                raise HTTPException(status_code=400, detail="Verification code is not initialized")
            if not _verify_code_hash(raw_code, record.verification_code_hash):
                _record_failed_attempt(record, now)
                failure_detail = "Invalid verification code"

        if failure_detail is None:
            record.verified = True
            record.failed_attempts = 0
            record.locked_until = None
            record.verification_code_hash = None

    if failure_detail is not None:
        raise HTTPException(status_code=400, detail=failure_detail)

    return {"success": True, "message": "2FA verified"}


@router.post("/2fa/challenge", summary="Start login 2FA step-up challenge")
def start_login_2fa_challenge(payload: TwoFAChallengeRequest, request: Request, user: User = CurrentUser) -> dict:
    now = datetime.now(tz=timezone.utc)
    current_context = auth_service.get_current_context(request)
    current_session_id = str(current_context.session.id)

    with get_session() as session:
        session_record = session.execute(
            select(UserSession).where(UserSession.id == current_session_id)
        ).scalar_one_or_none()
        if session_record is None:
            raise HTTPException(status_code=401, detail="Invalid session")

        trusted_expires = session_record.high_trust_expires_at
        if trusted_expires is not None:
            effective = trusted_expires if trusted_expires.tzinfo else trusted_expires.replace(tzinfo=timezone.utc)
            if effective > now:
                return {
                    "success": True,
                    "method": "trusted_device",
                    "high_trust_until": effective.isoformat(),
                    "challenge_required": False,
                }

        if _is_locked(session_record.twofa_locked_until, now):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later")

        method = _resolve_login_2fa_method(user, payload.fallbackMethod)
        session_record.twofa_challenge_method = method
        session_record.twofa_challenge_expires_at = now + timedelta(minutes=settings.otp_code_ttl_minutes)

        if method == "totp":
            session_record.twofa_challenge_code_hash = None
        elif method == "sms":
            phone = _normalize_phone_number(payload.phoneNumber or user.phone_number or user.twofa_secret)
            if not phone:
                raise HTTPException(status_code=400, detail="Valid E.164 phone number is required for SMS 2FA")
            twofa_service.send_sms_verify(phone_number=phone)
            session_record.twofa_challenge_code_hash = None
        else:
            code = _generate_verification_code()
            twofa_service.send_email_code(to_email=str(user.email), code=code)
            session_record.twofa_challenge_code_hash = _hash_verification_code(code)

        session_record.twofa_failed_attempts = 0
        session_record.twofa_locked_until = None
        session_record.twofa_required = True

    _write_auth_audit(
        event_type="2fa_challenge",
        status="success",
        request=request,
        user=user,
        method=method,
    )

    return {
        "success": True,
        "method": method,
        "expires_in_seconds": settings.otp_code_ttl_minutes * 60,
        "challenge_required": True,
    }


@router.post("/2fa/verify", summary="Complete login 2FA step-up and issue high-trust session")
def verify_login_2fa(payload: TwoFAVerifyRequest, request: Request, user: User = CurrentUser) -> dict:
    now = datetime.now(tz=timezone.utc)
    current_context = auth_service.get_current_context(request)
    current_session_id = str(current_context.session.id)
    method: str = ""
    invalid_code = False

    with get_session() as session:
        session_record = session.execute(
            select(UserSession).where(UserSession.id == current_session_id)
        ).scalar_one_or_none()
        if session_record is None:
            raise HTTPException(status_code=401, detail="Invalid session")

        if _is_locked(session_record.twofa_locked_until, now):
            raise HTTPException(status_code=429, detail="Too many failed attempts. Try again later")

        method = str(session_record.twofa_challenge_method or "")
        if method not in {"totp", "sms", "email"}:
            method = _resolve_login_2fa_method(user)

        expires_at = session_record.twofa_challenge_expires_at
        if expires_at is not None:
            effective_exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
            if effective_exp <= now:
                raise HTTPException(status_code=410, detail="2FA challenge expired")

        code = str(payload.verificationCode or "").strip()
        verified = False
        if method == "totp":
            verified = twofa_service.verify_totp(secret=str(user.twofa_secret or ""), code=code)
        elif method == "sms":
            phone = _normalize_phone_number(user.phone_number or user.twofa_secret)
            if not phone:
                raise HTTPException(status_code=400, detail="No valid SMS destination is configured")
            verified = twofa_service.verify_sms_code(phone_number=phone, code=code)
        else:
            verified = _verify_code_hash(code, session_record.twofa_challenge_code_hash)

        if not verified:
            session_record.twofa_failed_attempts = int(session_record.twofa_failed_attempts or 0) + 1
            if session_record.twofa_failed_attempts >= max(1, int(settings.otp_max_attempts)):
                session_record.twofa_locked_until = now + timedelta(minutes=max(1, int(settings.otp_lockout_minutes)))
            invalid_code = True

    if invalid_code:
        _write_auth_audit(
            event_type="2fa_verify",
            status="failed",
            request=request,
            user=user,
            method=method,
        )
        raise HTTPException(status_code=400, detail="Invalid verification code")

    auth_service.mark_session_high_trust(request=request)
    if payload.trustDevice:
        auth_service.trust_current_device(user_id=str(user.id), request=request, label=payload.deviceLabel)

    _send_security_alert_for_request(
        user=user,
        method=method,
        request=request,
        event="2FA verification completed",
    )
    _write_auth_audit(
        event_type="2fa_verify",
        status="success",
        request=request,
        user=user,
        method=method,
        metadata={"trusted_device": bool(payload.trustDevice)},
    )

    refreshed_context = auth_service.get_current_context(request)
    high_trust_until = refreshed_context.session.high_trust_expires_at
    if high_trust_until is not None and high_trust_until.tzinfo is None:
        high_trust_until = high_trust_until.replace(tzinfo=timezone.utc)
    return {
        "success": True,
        "high_trust_until": high_trust_until.isoformat() if high_trust_until else None,
        "method": method,
        "trusted_device": bool(payload.trustDevice),
    }


@router.get("/session/high-trust-status", summary="Check if current session has elevated trust")
def high_trust_status(request: Request, user: User = CurrentUser) -> dict:
    now = datetime.now(tz=timezone.utc)
    context = auth_service.get_current_context(request)
    session_record = context.session
    exp = session_record.high_trust_expires_at
    if exp is None:
        return {
            "high_trust": False,
            "expires_at": None,
            "user": str(user.email),
            "step_up_required": bool(session_record.twofa_required),
            "risk_score": int(session_record.risk_score or 0),
            "risk_reasons": json.loads(str(session_record.risk_reasons_json or "[]")),
        }
    effective = exp if exp.tzinfo else exp.replace(tzinfo=timezone.utc)
    return {
        "high_trust": effective > now,
        "expires_at": effective.isoformat(),
        "user": str(user.email),
        "step_up_required": bool(session_record.twofa_required),
        "risk_score": int(session_record.risk_score or 0),
        "risk_reasons": json.loads(str(session_record.risk_reasons_json or "[]")),
    }


@router.get("/devices/trusted", summary="List trusted devices for the current user")
def list_trusted_devices(user: User = CurrentUser) -> dict:
    with get_session() as session:
        rows = session.execute(
            select(TrustedDevice)
            .where(TrustedDevice.user_id == str(user.id))
            .order_by(TrustedDevice.last_seen_at.desc())
        ).scalars().all()

    devices = [
        TrustedDeviceResponse(
            id=row.id,
            label=row.label,
            first_seen_at=row.first_seen_at.isoformat(),
            last_seen_at=row.last_seen_at.isoformat(),
            trusted_until=row.trusted_until.isoformat(),
            last_ip_address=row.last_ip_address,
        ).model_dump()
        for row in rows
    ]
    return {"devices": devices}


@router.post("/devices/trust-current", summary="Mark current device as trusted")
def trust_current_device(payload: WebAuthnChallengeRequest, request: Request, user: User = CurrentUser) -> dict:
    auth_service.trust_current_device(user_id=str(user.id), request=request, label=payload.deviceLabel)
    _write_auth_audit(
        event_type="trusted_device",
        status="success",
        request=request,
        user=user,
        method="device_registry",
    )
    return {"success": True}


@router.delete("/devices/trusted/{device_id}", summary="Revoke a trusted device")
def revoke_trusted_device(device_id: int, request: Request, user: User = CurrentUser) -> dict:
    deleted = False
    with get_session() as session:
        row = session.execute(
            select(TrustedDevice)
            .where(TrustedDevice.id == device_id)
            .where(TrustedDevice.user_id == str(user.id))
        ).scalar_one_or_none()
        if row is not None:
            session.delete(row)
            deleted = True

    if deleted:
        _write_auth_audit(
            event_type="trusted_device_revoke",
            status="success",
            request=request,
            user=user,
            method="device_registry",
            metadata={"device_id": device_id},
        )
    return {"success": True, "deleted": deleted}


@router.post("/webauthn/register/challenge", summary="Create WebAuthn registration challenge")
def webauthn_register_challenge(payload: WebAuthnRegisterChallengeRequest, request: Request, user: User = CurrentUser) -> dict:
    now = datetime.now(tz=timezone.utc)
    _purge_expired_webauthn_challenges(now)

    challenge_id = secrets.token_urlsafe(24)
    challenge = secrets.token_urlsafe(32)
    ttl_seconds = max(30, int(settings.webauthn_challenge_ttl_seconds))
    expires_at = now + timedelta(seconds=ttl_seconds)

    _webauthn_challenges[challenge_id] = {
        "purpose": "registration",
        "challenge": challenge,
        "user_id": str(user.id),
        "expires_at": expires_at,
        "device_fingerprint_hash": auth_service._compute_device_fingerprint(request),
        "device_label": payload.deviceLabel,
    }

    _write_auth_audit(
        event_type="webauthn_registration_challenge",
        status="success",
        request=request,
        user=user,
        method="webauthn",
    )
    return {
        "success": True,
        "challengeId": challenge_id,
        "challenge": challenge,
        "rpId": settings.webauthn_rp_id,
        "origin": settings.webauthn_rp_origin,
        "timeoutMs": ttl_seconds * 1000,
    }


@router.post("/webauthn/register", summary="Register a WebAuthn credential")
def webauthn_register(payload: WebAuthnRegisterRequest, request: Request, user: User = CurrentUser) -> dict:
    now = datetime.now(tz=timezone.utc)
    _purge_expired_webauthn_challenges(now)
    challenge_payload = _webauthn_challenges.pop(payload.challengeId, None)
    if challenge_payload is None or str(challenge_payload.get("purpose")) != "registration":
        raise HTTPException(status_code=400, detail="Invalid or expired WebAuthn registration challenge")
    if str(challenge_payload.get("user_id") or "") != str(user.id):
        raise HTTPException(status_code=403, detail="WebAuthn challenge user mismatch")

    try:
        VerifyingKey.from_pem(payload.publicKeyPem)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid public key format")

    with get_session() as session:
        row = session.execute(
            select(WebAuthnCredential)
            .where(WebAuthnCredential.user_id == str(user.id))
            .where(WebAuthnCredential.credential_id == payload.credentialId)
        ).scalar_one_or_none()
        if row is None:
            row = WebAuthnCredential(
                user_id=str(user.id),
                credential_id=payload.credentialId,
                public_key_pem=payload.publicKeyPem,
                algorithm=payload.algorithm,
                sign_count=max(0, int(payload.signCount)),
                device_fingerprint_hash=auth_service._compute_device_fingerprint(request),
                label=str(challenge_payload.get("device_label") or "") or None,
                transports_json=json.dumps(payload.transports or []),
                created_at=now,
            )
            session.add(row)
        else:
            row.public_key_pem = payload.publicKeyPem
            row.algorithm = payload.algorithm
            row.sign_count = max(row.sign_count, int(payload.signCount))
            row.device_fingerprint_hash = auth_service._compute_device_fingerprint(request)
            row.transports_json = json.dumps(payload.transports or [])
            row.last_used_at = now

    auth_service.trust_current_device(user_id=str(user.id), request=request, label=str(challenge_payload.get("device_label") or None))
    _write_auth_audit(
        event_type="webauthn_registration",
        status="success",
        request=request,
        user=user,
        method="webauthn",
        metadata={"credential_id": payload.credentialId},
    )
    return {"success": True, "credentialId": payload.credentialId}


@router.post("/webauthn/challenge", summary="Create a WebAuthn assertion challenge for step-up")
def webauthn_challenge(payload: WebAuthnChallengeRequest, request: Request, user: User = CurrentUser) -> dict:
    now = datetime.now(tz=timezone.utc)
    _purge_expired_webauthn_challenges(now)

    challenge_id = secrets.token_urlsafe(24)
    challenge = secrets.token_urlsafe(32)
    ttl_seconds = max(30, int(settings.webauthn_challenge_ttl_seconds))
    expires_at = now + timedelta(seconds=ttl_seconds)

    _webauthn_challenges[challenge_id] = {
        "purpose": "assertion",
        "challenge": challenge,
        "user_id": str(user.id),
        "expires_at": expires_at,
        "device_fingerprint_hash": auth_service._compute_device_fingerprint(request),
        "device_label": payload.deviceLabel,
    }

    with get_session() as session:
        credentials = session.execute(
            select(WebAuthnCredential)
            .where(WebAuthnCredential.user_id == str(user.id))
            .order_by(WebAuthnCredential.created_at.desc())
        ).scalars().all()

    _write_auth_audit(
        event_type="webauthn_challenge",
        status="success",
        request=request,
        user=user,
        method="webauthn",
    )

    return {
        "success": True,
        "challengeId": challenge_id,
        "challenge": challenge,
        "rpId": settings.webauthn_rp_id,
        "origin": settings.webauthn_rp_origin,
        "timeoutMs": ttl_seconds * 1000,
        "userVerification": "required",
        "allowCredentials": [
            {"id": item.credential_id, "transports": json.loads(str(item.transports_json or "[]"))}
            for item in credentials
        ],
        "challengeRequired": True,
    }


@router.post("/webauthn/verify", summary="Verify WebAuthn assertion and mark session high trust")
def webauthn_verify(payload: WebAuthnVerifyRequest, request: Request, user: User = CurrentUser) -> dict:
    now = datetime.now(tz=timezone.utc)
    _purge_expired_webauthn_challenges(now)

    challenge_payload = _webauthn_challenges.pop(payload.challengeId, None)
    if challenge_payload is None or str(challenge_payload.get("purpose")) != "assertion":
        raise HTTPException(status_code=400, detail="Invalid or expired WebAuthn challenge")
    if str(challenge_payload.get("user_id") or "") != str(user.id):
        raise HTTPException(status_code=403, detail="WebAuthn challenge user mismatch")

    with get_session() as session:
        credential = session.execute(
            select(WebAuthnCredential)
            .where(WebAuthnCredential.user_id == str(user.id))
            .where(WebAuthnCredential.credential_id == payload.credentialId)
        ).scalar_one_or_none()
        if credential is None:
            raise HTTPException(status_code=404, detail="WebAuthn credential is not registered")

        fingerprint_hash = auth_service._compute_device_fingerprint(request)
        if credential.device_fingerprint_hash and credential.device_fingerprint_hash != fingerprint_hash:
            raise HTTPException(status_code=403, detail="Credential is bound to a different device")

        try:
            client_data, client_data_raw = _decode_webauthn_client_data(payload.clientDataJSON)
            auth_data_raw, flags, sign_count = _decode_authenticator_data(payload.authenticatorData)
            rp_hash = auth_data_raw[:32]
            expected_rp_hash = hashlib.sha256(str(settings.webauthn_rp_id).encode("utf-8")).digest()
            if rp_hash != expected_rp_hash:
                raise HTTPException(status_code=400, detail="WebAuthn rpId hash mismatch")
            if (flags & 0x01) == 0 or (flags & 0x04) == 0:
                raise HTTPException(status_code=400, detail="WebAuthn user presence/verification failed")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid WebAuthn assertion payload")

        if str(client_data.get("type") or "") != "webauthn.get":
            raise HTTPException(status_code=400, detail="Invalid WebAuthn assertion type")
        if str(client_data.get("challenge") or "") != str(challenge_payload.get("challenge") or ""):
            raise HTTPException(status_code=400, detail="WebAuthn challenge mismatch")

        expected_origin = str(settings.webauthn_rp_origin or "").strip()
        received_origin = str(client_data.get("origin") or "").strip()
        if expected_origin and received_origin and received_origin != expected_origin:
            raise HTTPException(status_code=400, detail="WebAuthn origin mismatch")

        try:
            _verify_webauthn_signature(
                public_key_pem=credential.public_key_pem,
                signature_b64=payload.signature,
                authenticator_data_raw=auth_data_raw,
                client_data_raw=client_data_raw,
            )
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid WebAuthn signature")

        if sign_count > int(credential.sign_count or 0):
            credential.sign_count = sign_count
        credential.last_used_at = now

    auth_service.mark_session_high_trust(request=request)
    auth_service.trust_current_device(user_id=str(user.id), request=request, label=str(challenge_payload.get("device_label") or None))

    _write_auth_audit(
        event_type="webauthn_assertion",
        status="success",
        request=request,
        user=user,
        method="webauthn",
        metadata={
            "credential_id": payload.credentialId,
            "verification": "signature_verified",
        },
    )
    _send_security_alert_for_request(
        user=user,
        method="webauthn",
        request=request,
        event="Passkey verification completed",
    )

    refreshed_context = auth_service.get_current_context(request)
    high_trust_until = refreshed_context.session.high_trust_expires_at
    if high_trust_until is not None and high_trust_until.tzinfo is None:
        high_trust_until = high_trust_until.replace(tzinfo=timezone.utc)
    return {
        "success": True,
        "method": "webauthn",
        "high_trust_until": high_trust_until.isoformat() if high_trust_until else None,
    }


@router.post("/signup-complete", response_model=AuthResponse, summary="Complete account creation")
def signup_complete(payload: SignupCompleteRequest, request: Request, response: Response) -> AuthResponse:
    email = auth_service._normalize_email(payload.email)
    auth_service.validate_password_strength(payload.password)

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
    email = auth_service._normalize_email(payload.email)
    now = datetime.now(tz=timezone.utc)
    state = _load_login_security_state(email)
    if state and state.locked_until is not None:
        locked_until = state.locked_until if state.locked_until.tzinfo else state.locked_until.replace(tzinfo=timezone.utc)
        if locked_until > now:
            _write_auth_audit(
                event_type="login",
                status="blocked_locked",
                request=request,
                email=email,
                method="password",
                metadata={"locked_until": locked_until.isoformat()},
            )
            raise HTTPException(status_code=429, detail="Account temporarily locked due to repeated failed logins")

    if state and int(state.failed_attempts or 0) >= max(1, int(settings.login_progressive_delay_after_failures)):
        time.sleep(max(0, int(settings.login_progressive_delay_seconds)))

    try:
        user = auth_service.authenticate_user(email=email, password=payload.password)
    except HTTPException:
        failed_count, locked_until = _record_login_failure(email, now)
        _write_auth_audit(
            event_type="login",
            status="failed",
            request=request,
            email=email,
            method="password",
            metadata={
                "failed_attempts": failed_count,
                "locked_until": locked_until.isoformat() if locked_until else None,
            },
        )
        raise

    _clear_login_failures(email)
    auth_service.issue_login_cookie(response=response, user_id=str(user.id), request=request)
    _send_security_alert_for_request(
        user=user,
        method="session_start",
        request=request,
        event="New login detected",
    )
    _write_auth_audit(
        event_type="login",
        status="success",
        request=request,
        user=user,
        method="password",
    )
    return AuthResponse(user=_serialize_user(user))


@router.post("/refresh", response_model=AuthResponse, summary="Rotate refresh token and issue a new access token")
def refresh_session(request: Request, response: Response) -> AuthResponse:
    user = auth_service.rotate_session_tokens(request=request, response=response)
    _write_auth_audit(
        event_type="token_refresh",
        status="success",
        request=request,
        user=user,
        method="refresh_token",
    )
    return AuthResponse(user=_serialize_user(user))


@router.post("/forgot-password", summary="Request password reset link")
def forgot_password(payload: ForgotPasswordRequest, request: Request) -> dict:
    email = auth_service._normalize_email(payload.email)
    now = datetime.now(tz=timezone.utc)
    client_ip = _extract_client_ip(request)

    ip_attempts, ip_blocked = _consume_rate_limit(
        scope="forgot_password:ip",
        key_value=client_ip,
        now=now,
        max_attempts=settings.password_reset_request_max_per_ip,
        window_minutes=settings.password_reset_request_window_minutes,
    )
    if ip_blocked:
        raise HTTPException(status_code=429, detail="Too many password reset requests. Try again later")

    if email:
        _, email_blocked = _consume_rate_limit(
            scope="forgot_password:email",
            key_value=email,
            now=now,
            max_attempts=settings.password_reset_request_max_per_email,
            window_minutes=settings.password_reset_request_window_minutes,
        )
        if email_blocked:
            raise HTTPException(status_code=429, detail="Too many password reset requests. Try again later")

    if _requires_forgot_password_captcha(ip_attempts=ip_attempts) and settings.turnstile_secret_key:
        captcha_token = str(payload.captchaToken or "").strip()
        if not captcha_token or not _verify_turnstile_token(token=captcha_token, remote_ip=client_ip):
            raise HTTPException(status_code=429, detail="Captcha verification required")

    if "@" not in email or len(email) < 5:
        # Preserve anti-enumeration response shape for invalid/missing accounts.
        return {
            "success": True,
            "message": "If that email is registered, a password reset link has been sent.",
        }

    with get_session() as session:
        user = session.execute(select(User).where(User.email == email)).scalar_one_or_none()
        if user is None:
            _write_auth_audit(
                event_type="password_reset_request",
                status="unknown_account",
                request=request,
                email=email,
                method="email",
            )
            return {
                "success": True,
                "message": "If that email is registered, a password reset link has been sent.",
            }

        user_id = str(user.id)
        session.query(PasswordResetToken).filter(PasswordResetToken.user_id == user_id).delete()

        raw_token = secrets.token_urlsafe(36)
        token_hash = _hash_reset_token(raw_token)
        expires_at = now + timedelta(minutes=max(1, int(settings.password_reset_ttl_minutes)))
        session.add(
            PasswordResetToken(
                user_id=user_id,
                token_hash=token_hash,
                created_at=now,
                expires_at=expires_at,
                failed_attempts=0,
                max_attempts=max(1, int(settings.password_reset_max_attempts)),
                used_at=None,
            )
        )

    reset_link = f"{settings.frontend_base_url.rstrip('/')}/login?reset_token={raw_token}"
    try:
        twofa_service.send_password_reset_email(to_email=email, reset_link=reset_link)
    except Exception:
        # Keep response shape identical to avoid account enumeration hints.
        pass
    try:
        twofa_service.send_security_alert(
            to_email=email,
            method="password_reset",
            ip_address=client_ip,
            device=request.headers.get("user-agent"),
            event="Password reset requested",
        )
    except Exception:
        pass
    _write_auth_audit(
        event_type="password_reset_request",
        status="success",
        request=request,
        email=email,
        method="email",
    )

    return {
        "success": True,
        "message": "If that email is registered, a password reset link has been sent.",
    }


@router.post("/reset-password", summary="Complete password reset with reset token")
def reset_password(payload: ResetPasswordRequest, request: Request) -> dict:
    now = datetime.now(tz=timezone.utc)
    client_ip = _extract_client_ip(request)
    _, ip_blocked = _consume_rate_limit(
        scope="reset_password:ip",
        key_value=client_ip,
        now=now,
        max_attempts=settings.password_reset_submit_max_per_ip,
        window_minutes=settings.password_reset_submit_window_minutes,
    )
    if ip_blocked:
        raise HTTPException(status_code=429, detail="Too many reset attempts. Try again later")

    token = str(payload.token or "").strip()
    if len(token) < 16:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    auth_service.validate_password_strength(payload.newPassword)

    token_hash = _hash_reset_token(token)

    user_email: str | None = None
    reset_user_id: str | None = None
    with get_session() as session:
        record = session.execute(
            select(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
        ).scalar_one_or_none()

        if record is None:
            _write_auth_audit(
                event_type="password_reset",
                status="invalid_token",
                request=request,
                method="token",
            )
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        if record.used_at is not None:
            _write_auth_audit(
                event_type="password_reset",
                status="replay_blocked",
                request=request,
                method="token",
            )
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        if int(record.failed_attempts or 0) >= max(1, int(record.max_attempts or settings.password_reset_max_attempts)):
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        expires_at = record.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            record.failed_attempts = int(record.failed_attempts or 0) + 1
            if int(record.failed_attempts) >= max(1, int(record.max_attempts or settings.password_reset_max_attempts)):
                record.used_at = now
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        user = session.execute(select(User).where(User.id == record.user_id)).scalar_one_or_none()
        if user is None:
            record.failed_attempts = int(record.failed_attempts or 0) + 1
            raise HTTPException(status_code=400, detail="Invalid or expired reset token")

        user.password_hash = auth_service._hash_password(payload.newPassword)
        user.updated_at = now
        user_email = str(user.email)
        reset_user_id = str(user.id)
        record.used_at = now
        session.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == str(user.id),
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.id != record.id,
        ).delete()

    if reset_user_id:
        auth_service.revoke_all_user_sessions(user_id=reset_user_id)
    if user_email:
        try:
            twofa_service.send_security_alert(
                to_email=user_email,
                method="password_reset",
                ip_address=client_ip,
                device=request.headers.get("user-agent"),
                event="Password reset completed",
            )
        except Exception:
            pass
    _write_auth_audit(
        event_type="password_reset",
        status="success",
        request=request,
        email=user_email,
        method="token",
    )

    return {"success": True, "message": "Password has been reset"}


@router.post("/logout", summary="Revoke current session and clear auth cookie")
def logout(request: Request, response: Response) -> dict:
    try:
        user = auth_service.get_current_user(request)
    except HTTPException:
        user = None
    auth_service.revoke_current_session(request)
    auth_service.clear_login_cookie(response=response)
    _write_auth_audit(
        event_type="logout",
        status="success",
        request=request,
        user=user,
        method="session",
    )
    return {"ok": True}


@router.get("/me", response_model=AuthResponse, summary="Current authenticated user")
def me(user: User = CurrentUser) -> AuthResponse:
    return AuthResponse(user=_serialize_user(user))


def _is_configured_env(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized not in {"", "none", "null"}


@router.get("/provider-status", summary="Check which 2FA providers are configured (no secrets exposed)")
def provider_status() -> dict:
    """Returns True/False for each provider based on whether required env vars are non-empty.
    Useful for diagnosing misconfigured credentials without exposing values."""
    twilio_creds_ok = _is_configured_env(settings.twilio_account_sid) and _is_configured_env(settings.twilio_auth_token)
    verify_ok = twilio_creds_ok and _is_configured_env(settings.twilio_verify_service_sid)
    sendgrid_ok = _is_configured_env(settings.sendgrid_api_key) and _is_configured_env(settings.sendgrid_from)
    smtp_ok = _is_configured_env(settings.smtp_host) and _is_configured_env(settings.smtp_from_email)

    return {
        "totp": True,  # always available (pyotp is bundled)
        "sms_twilio_verify": verify_ok,
        "twilio_account_sid_prefix": (settings.twilio_account_sid or "")[:6] + "…" if settings.twilio_account_sid else "(not set)",
        "twilio_verify_service_sid_prefix": (settings.twilio_verify_service_sid or "")[:6] + "…" if settings.twilio_verify_service_sid else "(not set)",
        "email_sendgrid": sendgrid_ok,
        "email_smtp": smtp_ok,
        "sendgrid_from": settings.sendgrid_from or "(not set)",
        "smtp_host": settings.smtp_host or "(not set)",
    }


@router.get("/alpaca/callback", summary="OAuth callback compatibility route")
def alpaca_callback_compat(code: str, state: str) -> RedirectResponse:
    qs = urlencode({"code": code, "state": state})
    return RedirectResponse(url=f"/alpaca/oauth/callback?{qs}", status_code=307)


@router.get("/schwab/callback", summary="Charles Schwab OAuth callback route")
def schwab_callback(request: Request, code: str, state: str) -> RedirectResponse:
    return _complete_schwab_oauth(request=request, code=code, state=state)


@router.get("/schwab/oauth/start", summary="Start Charles Schwab OAuth flow")
def start_schwab_oauth() -> RedirectResponse:
    if not settings.schwab_client_id or not settings.schwab_redirect_uri:
        raise HTTPException(
            status_code=500,
            detail="Schwab OAuth not configured. Set SCHWAB_CLIENT_ID and SCHWAB_REDIRECT_URI.",
        )

    state = secrets.token_urlsafe(24)
    query = {
        "client_id": settings.schwab_client_id,
        "redirect_uri": settings.schwab_redirect_uri,
        "response_type": "code",
        "state": state,
    }
    auth_url = f"{settings.schwab_authorize_url}?{urlencode(query)}"
    return RedirectResponse(url=auth_url, status_code=307)


@router.get("/schwab/oauth/callback", summary="Charles Schwab OAuth callback compatibility route")
def schwab_oauth_callback(request: Request, code: str, state: str) -> RedirectResponse:
    return _complete_schwab_oauth(request=request, code=code, state=state)


def _complete_schwab_oauth(*, request: Request, code: str, state: str) -> RedirectResponse:
    if not settings.schwab_client_id or not settings.schwab_client_secret or not settings.schwab_redirect_uri:
        raise HTTPException(
            status_code=500,
            detail=(
                "Schwab OAuth not configured. Set SCHWAB_CLIENT_ID, "
                "SCHWAB_CLIENT_SECRET, and SCHWAB_REDIRECT_URI."
            ),
        )

    # Schwab requires HTTP Basic auth with client_id:client_secret for token exchange.
    basic = base64.b64encode(f"{settings.schwab_client_id}:{settings.schwab_client_secret}".encode("utf-8")).decode("utf-8")
    token_body = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": settings.schwab_redirect_uri,
    }

    try:
        with httpx.Client(timeout=20) as client:
            token_resp = client.post(
                settings.schwab_token_url,
                data=token_body,
                headers={
                    "Authorization": f"Basic {basic}",
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                },
            )
        token_resp.raise_for_status()
        payload = token_resp.json()
    except httpx.HTTPStatusError as err:
        detail = err.response.text if err.response is not None else str(err)
        status = err.response.status_code if err.response is not None else 502
        raise HTTPException(status_code=status, detail=f"Schwab token exchange failed: {detail}") from err
    except Exception as err:
        raise HTTPException(status_code=502, detail=f"Schwab token exchange failed: {err}") from err

    try:
        user = auth_service.get_current_user(request)
    except HTTPException as err:
        raise HTTPException(
            status_code=401,
            detail=(
                "Schwab token exchange succeeded, but no authenticated session was found to bind this broker "
                "connection. Sign in and start OAuth from the app so cookies/state are present."
            ),
        ) from err

    now = datetime.now(timezone.utc)
    expires_in_raw = payload.get("expires_in")
    expires_in: int | None = None
    if expires_in_raw is not None:
        try:
            expires_in = int(expires_in_raw)
        except (TypeError, ValueError):
            expires_in = None

    with get_session() as session:
        connection = session.execute(
            select(BrokerOAuthConnection).where(
                BrokerOAuthConnection.user_id == str(user.id),
                BrokerOAuthConnection.provider == "schwab",
            )
        ).scalar_one_or_none()
        if connection is None:
            connection = BrokerOAuthConnection(user_id=str(user.id), provider="schwab")
            session.add(connection)

        connection.connected = bool(payload.get("access_token"))
        connection.access_token = payload.get("access_token")
        connection.refresh_token = payload.get("refresh_token")
        connection.token_type = payload.get("token_type")
        scope_value = payload.get("scope")
        connection.scope = str(scope_value) if scope_value is not None else None
        connection.expires_in = expires_in
        connection.obtained_at = now
        connection.disconnected_at = None
        connection.last_error = None
        connection.updated_at = now
        session.flush()

    redirect_base = (settings.frontend_base_url or "http://localhost:3000").rstrip("/")
    redirect_url = f"{redirect_base}/brokerages?schwab_oauth={'connected' if payload.get('access_token') else 'error'}"
    return RedirectResponse(url=redirect_url, status_code=307)
