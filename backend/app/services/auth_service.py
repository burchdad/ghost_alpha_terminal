from __future__ import annotations

import base64
import json
import hashlib
import hmac
import os
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response
from sqlalchemy import select

from app.core.config import settings
from app.db.models import TrustedDevice, User, UserSession
from app.db.session import get_session


@dataclass
class SessionUserContext:
    user: User
    session: UserSession


class AuthService:
    ACCESS_COOKIE_NAME = "ghost_auth_access"
    SESSION_COOKIE_NAME = "ghost_auth_session"
    SESSION_TTL_DAYS = 14
    ACCESS_TTL_MINUTES = 30
    PASSWORD_ITERATIONS = 210_000
    _COMMON_PASSWORDS = {
        "password",
        "password123",
        "12345678",
        "qwerty123",
        "letmein",
        "admin123",
        "welcome1",
        "iloveyou",
    }
    DEFENSIVE_RISK_THRESHOLD = 40

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(tz=timezone.utc)

    @staticmethod
    def _normalize_email(email: str) -> str:
        return str(email or "").strip().lower()

    @staticmethod
    def _hash_password(password: str) -> str:
        salt = os.urandom(16)
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            AuthService.PASSWORD_ITERATIONS,
        )
        return (
            f"pbkdf2_sha256${AuthService.PASSWORD_ITERATIONS}$"
            f"{base64.urlsafe_b64encode(salt).decode('utf-8')}$"
            f"{base64.urlsafe_b64encode(derived).decode('utf-8')}"
        )

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        try:
            algorithm, iterations_str, salt_b64, hash_b64 = password_hash.split("$", 3)
            if algorithm != "pbkdf2_sha256":
                return False
            iterations = int(iterations_str)
            salt = base64.urlsafe_b64decode(salt_b64.encode("utf-8"))
            expected = base64.urlsafe_b64decode(hash_b64.encode("utf-8"))
            candidate = hashlib.pbkdf2_hmac(
                "sha256",
                password.encode("utf-8"),
                salt,
                iterations,
            )
            return hmac.compare_digest(expected, candidate)
        except Exception:
            return False

    @staticmethod
    def _session_token_hash(token: str) -> str:
        secret = settings.auth_session_secret or "ghost-alpha-dev-session-secret"
        return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _ip_prefix(ip: str | None, prefix_length: int) -> str:
        raw = str(ip or "").strip()
        if not raw:
            return ""
        if "." in raw and raw.count(".") == 3:
            octets = raw.split(".")
            keep = max(1, min(4, int(prefix_length) // 8))
            return ".".join(octets[:keep])
        if ":" in raw:
            chunks = raw.split(":")
            keep = max(1, min(len(chunks), int(prefix_length) // 16))
            return ":".join(chunks[:keep])
        return raw[: max(1, int(prefix_length))]

    @classmethod
    def validate_password_strength(cls, password: str) -> None:
        candidate = str(password or "")
        if len(candidate) < 10:
            raise HTTPException(status_code=400, detail="Password must be at least 10 characters")
        if len(candidate) > 128:
            raise HTTPException(status_code=400, detail="Password must be at most 128 characters")
        if not re.search(r"[A-Z]", candidate):
            raise HTTPException(status_code=400, detail="Password must include an uppercase letter")
        if not re.search(r"[a-z]", candidate):
            raise HTTPException(status_code=400, detail="Password must include a lowercase letter")
        if not re.search(r"[0-9]", candidate):
            raise HTTPException(status_code=400, detail="Password must include a number")
        if not re.search(r"[^A-Za-z0-9]", candidate):
            raise HTTPException(status_code=400, detail="Password must include a symbol")
        if candidate.lower() in cls._COMMON_PASSWORDS:
            raise HTTPException(status_code=400, detail="Password is too common")

    @staticmethod
    def _parse_client_ip(request: Request) -> str | None:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidate = forwarded.split(",", 1)[0].strip()
            if candidate:
                return candidate
        return request.client.host if request.client else None

    @staticmethod
    def _compute_device_fingerprint(request: Request) -> str:
        supplied = str(request.headers.get("x-device-fingerprint") or "").strip()
        ua = str(request.headers.get("user-agent") or "").strip()
        base = supplied if supplied else ua
        if not base:
            base = "unknown-device"
        return hashlib.sha256(base.encode("utf-8")).hexdigest()

    def _cookie_secure(self) -> bool:
        return bool(settings.auth_cookie_secure)

    def _cookie_samesite(self) -> str:
        value = str(settings.auth_cookie_samesite or "lax").lower().strip()
        if value not in {"lax", "strict", "none"}:
            return "lax"
        return value

    def get_current_session_token_hash(self, request: Request) -> str:
        raw_token = request.cookies.get(self.ACCESS_COOKIE_NAME) or request.cookies.get(self.SESSION_COOKIE_NAME)
        if not raw_token:
            raise HTTPException(status_code=401, detail="Authentication required")
        return self._session_token_hash(raw_token)

    def create_user(self, *, email: str, password: str) -> User:
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            raise HTTPException(status_code=400, detail="Email is required")
        self.validate_password_strength(password)

        with get_session() as session:
            existing = session.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
            if existing is not None:
                raise HTTPException(status_code=409, detail="Email is already registered")

            now = self._utcnow()
            user = User(
                email=normalized_email,
                password_hash=self._hash_password(password),
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            session.add(user)
            session.flush()
            return user

    def authenticate_user(self, *, email: str, password: str) -> User:
        normalized_email = self._normalize_email(email)
        with get_session() as session:
            user = session.execute(select(User).where(User.email == normalized_email)).scalar_one_or_none()
            if user is None or not user.is_active:
                raise HTTPException(status_code=401, detail="Invalid email or password")
            if not self._verify_password(password, str(user.password_hash)):
                raise HTTPException(status_code=401, detail="Invalid email or password")
            return user

    def _create_session(self, *, user_id: str, request: Request) -> tuple[str, str]:
        refresh_token = secrets.token_urlsafe(48)
        access_token = secrets.token_urlsafe(32)
        refresh_hash = self._session_token_hash(refresh_token)
        access_hash = self._session_token_hash(access_token)
        now = self._utcnow()
        refresh_ttl_days = max(1, int(settings.auth_refresh_ttl_days or self.SESSION_TTL_DAYS))
        access_ttl_minutes = max(1, int(settings.auth_access_ttl_minutes or self.ACCESS_TTL_MINUTES))
        expires_at = now + timedelta(days=refresh_ttl_days)
        access_expires_at = now + timedelta(minutes=access_ttl_minutes)
        fingerprint_hash = self._compute_device_fingerprint(request)
        current_ip = self._parse_client_ip(request)
        ip_prefix_len = max(4, int(settings.risk_new_ip_prefix_length))
        request_ip_prefix = self._ip_prefix(current_ip, ip_prefix_len)

        high_trust_expires_at: datetime | None = None
        twofa_required = True
        risk_score = 0
        risk_reasons: list[str] = []

        with get_session() as session:
            trusted = session.execute(
                select(TrustedDevice)
                .where(TrustedDevice.user_id == user_id)
                .where(TrustedDevice.device_fingerprint_hash == fingerprint_hash)
                .where(TrustedDevice.trusted_until > now)
            ).scalar_one_or_none()
            if trusted is not None:
                trusted_ip_prefix = self._ip_prefix(trusted.last_ip_address, ip_prefix_len)
                trusted.last_seen_at = now
                trusted.last_ip_address = current_ip
                trusted.last_user_agent = request.headers.get("user-agent")
                if trusted_ip_prefix and trusted_ip_prefix != request_ip_prefix:
                    risk_score += 35
                    risk_reasons.append("new_ip_prefix")
                else:
                    high_trust_expires_at = now + timedelta(minutes=settings.high_trust_session_minutes)
                    twofa_required = False
            else:
                risk_score += 50
                risk_reasons.append("new_device")

        with get_session() as session:
            record = UserSession(
                user_id=user_id,
                session_token_hash=refresh_hash,
                access_token_hash=access_hash,
                user_agent=request.headers.get("user-agent"),
                ip_address=current_ip,
                device_fingerprint_hash=fingerprint_hash,
                twofa_required=twofa_required,
                high_trust_expires_at=high_trust_expires_at,
                twofa_verified_at=now if high_trust_expires_at is not None else None,
                risk_score=risk_score,
                risk_reasons_json=json.dumps(risk_reasons),
                access_expires_at=access_expires_at,
                expires_at=expires_at,
                created_at=now,
                revoked_at=None,
            )
            session.add(record)

        return (refresh_token, access_token)

    def issue_login_cookie(self, *, response: Response, user_id: str, request: Request) -> None:
        refresh_token, access_token = self._create_session(user_id=user_id, request=request)
        persistent_cookie = bool(settings.auth_cookie_persistent)
        refresh_max_age = int(timedelta(days=max(1, int(settings.auth_refresh_ttl_days))).total_seconds()) if persistent_cookie else None
        access_max_age = int(timedelta(minutes=max(1, int(settings.auth_access_ttl_minutes))).total_seconds()) if persistent_cookie else None
        response.set_cookie(
            key=self.SESSION_COOKIE_NAME,
            value=refresh_token,
            httponly=True,
            secure=self._cookie_secure(),
            samesite=self._cookie_samesite(),
            max_age=refresh_max_age,
            path="/",
        )
        response.set_cookie(
            key=self.ACCESS_COOKIE_NAME,
            value=access_token,
            httponly=True,
            secure=self._cookie_secure(),
            samesite=self._cookie_samesite(),
            max_age=access_max_age,
            path="/",
        )

    def clear_login_cookie(self, *, response: Response) -> None:
        response.delete_cookie(
            key=self.SESSION_COOKIE_NAME,
            httponly=True,
            secure=self._cookie_secure(),
            samesite=self._cookie_samesite(),
            path="/",
        )
        response.delete_cookie(
            key=self.ACCESS_COOKIE_NAME,
            httponly=True,
            secure=self._cookie_secure(),
            samesite=self._cookie_samesite(),
            path="/",
        )

    def get_current_context(self, request: Request) -> SessionUserContext:
        access_token = request.cookies.get(self.ACCESS_COOKIE_NAME)
        refresh_token = request.cookies.get(self.SESSION_COOKIE_NAME)
        if not access_token and not refresh_token:
            raise HTTPException(status_code=401, detail="Authentication required")
        now = self._utcnow()

        with get_session() as session:
            row = None
            if access_token:
                access_hash = self._session_token_hash(access_token)
                row = session.execute(
                    select(UserSession, User)
                    .join(User, User.id == UserSession.user_id)
                    .where(UserSession.access_token_hash == access_hash)
                ).first()

            if row is None and refresh_token:
                # Backward compatibility for legacy sessions that only had the refresh cookie.
                refresh_hash = self._session_token_hash(refresh_token)
                row = session.execute(
                    select(UserSession, User)
                    .join(User, User.id == UserSession.user_id)
                    .where(UserSession.session_token_hash == refresh_hash)
                ).first()

            if row is None:
                raise HTTPException(status_code=401, detail="Invalid session")

            user_session, user = row
            if user_session.revoked_at is not None:
                raise HTTPException(status_code=401, detail="Session has been revoked")
            if user_session.expires_at.tzinfo is None:
                expires_at = user_session.expires_at.replace(tzinfo=timezone.utc)
            else:
                expires_at = user_session.expires_at.astimezone(timezone.utc)
            if expires_at <= now:
                raise HTTPException(status_code=401, detail="Session has expired")
            if user_session.access_expires_at is not None:
                access_expires = user_session.access_expires_at
                if access_expires.tzinfo is None:
                    access_expires = access_expires.replace(tzinfo=timezone.utc)
                if access_expires <= now and access_token:
                    raise HTTPException(status_code=401, detail="Access token expired")
            if not bool(user.is_active):
                raise HTTPException(status_code=403, detail="User is inactive")

            return SessionUserContext(user=user, session=user_session)

    def rotate_session_tokens(self, *, request: Request, response: Response) -> User:
        refresh_token = request.cookies.get(self.SESSION_COOKIE_NAME)
        if not refresh_token:
            raise HTTPException(status_code=401, detail="Refresh token required")

        refresh_hash = self._session_token_hash(refresh_token)
        now = self._utcnow()
        with get_session() as session:
            row = session.execute(
                select(UserSession, User)
                .join(User, User.id == UserSession.user_id)
                .where(UserSession.session_token_hash == refresh_hash)
            ).first()
            if row is None:
                raise HTTPException(status_code=401, detail="Invalid refresh token")

            user_session, user = row
            if user_session.revoked_at is not None:
                raise HTTPException(status_code=401, detail="Session has been revoked")
            refresh_expires = user_session.expires_at if user_session.expires_at.tzinfo else user_session.expires_at.replace(tzinfo=timezone.utc)
            if refresh_expires <= now:
                raise HTTPException(status_code=401, detail="Refresh token expired")

            new_refresh_token = secrets.token_urlsafe(48)
            new_access_token = secrets.token_urlsafe(32)
            user_session.session_token_hash = self._session_token_hash(new_refresh_token)
            user_session.access_token_hash = self._session_token_hash(new_access_token)
            user_session.expires_at = now + timedelta(days=max(1, int(settings.auth_refresh_ttl_days)))
            user_session.access_expires_at = now + timedelta(minutes=max(1, int(settings.auth_access_ttl_minutes)))

            persistent_cookie = bool(settings.auth_cookie_persistent)
            refresh_max_age = int(timedelta(days=max(1, int(settings.auth_refresh_ttl_days))).total_seconds()) if persistent_cookie else None
            access_max_age = int(timedelta(minutes=max(1, int(settings.auth_access_ttl_minutes))).total_seconds()) if persistent_cookie else None
            response.set_cookie(
                key=self.SESSION_COOKIE_NAME,
                value=new_refresh_token,
                httponly=True,
                secure=self._cookie_secure(),
                samesite=self._cookie_samesite(),
                max_age=refresh_max_age,
                path="/",
            )
            response.set_cookie(
                key=self.ACCESS_COOKIE_NAME,
                value=new_access_token,
                httponly=True,
                secure=self._cookie_secure(),
                samesite=self._cookie_samesite(),
                max_age=access_max_age,
                path="/",
            )

            return user

    def should_force_defensive(self, *, request: Request, signal_risk_high: bool) -> tuple[bool, list[str], int]:
        context = self.get_current_context(request)
        session = context.session
        reasons: list[str] = []
        risk_score = int(session.risk_score or 0)

        if bool(session.twofa_required):
            reasons.append("low_trust_session")
        if risk_score >= self.DEFENSIVE_RISK_THRESHOLD:
            reasons.append("elevated_session_risk")
        if signal_risk_high:
            reasons.append("high_risk_signal")

        should_force = signal_risk_high and (
            bool(session.twofa_required) or risk_score >= self.DEFENSIVE_RISK_THRESHOLD
        )
        return (should_force, reasons, risk_score)

    def get_current_user(self, request: Request) -> User:
        return self.get_current_context(request).user

    def require_high_trust_user(self, request: Request) -> User:
        context = self.get_current_context(request)
        now = self._utcnow()
        expires_at = context.session.high_trust_expires_at
        if expires_at is None:
            raise HTTPException(status_code=403, detail="2FA step-up required")
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise HTTPException(status_code=403, detail="High-trust session expired; re-verify 2FA")
        return context.user

    def mark_session_high_trust(self, *, request: Request) -> UserSession:
        access_token = request.cookies.get(self.ACCESS_COOKIE_NAME)
        if not access_token:
            raise HTTPException(status_code=401, detail="Authentication required")

        token_hash = self._session_token_hash(access_token)
        now = self._utcnow()
        high_trust_expires_at = now + timedelta(minutes=settings.high_trust_session_minutes)

        with get_session() as session:
            record = session.execute(
                select(UserSession).where(UserSession.access_token_hash == token_hash)
            ).scalar_one_or_none()
            if record is None:
                raise HTTPException(status_code=401, detail="Invalid session")
            record.twofa_required = False
            record.twofa_verified_at = now
            record.high_trust_expires_at = high_trust_expires_at
            record.twofa_failed_attempts = 0
            record.twofa_locked_until = None
            record.twofa_challenge_method = None
            record.twofa_challenge_code_hash = None
            record.twofa_challenge_expires_at = None
            session.flush()
            return record

    def trust_current_device(self, *, user_id: str, request: Request, label: str | None = None) -> None:
        now = self._utcnow()
        fingerprint_hash = self._compute_device_fingerprint(request)
        trusted_until = now + timedelta(days=settings.trusted_device_days)
        with get_session() as session:
            record = session.execute(
                select(TrustedDevice)
                .where(TrustedDevice.user_id == user_id)
                .where(TrustedDevice.device_fingerprint_hash == fingerprint_hash)
            ).scalar_one_or_none()
            if record is None:
                record = TrustedDevice(
                    user_id=user_id,
                    device_fingerprint_hash=fingerprint_hash,
                    label=label,
                    first_seen_at=now,
                    last_seen_at=now,
                    last_ip_address=self._parse_client_ip(request),
                    last_user_agent=request.headers.get("user-agent"),
                    trusted_until=trusted_until,
                )
                session.add(record)
                return

            record.label = label or record.label
            record.last_seen_at = now
            record.last_ip_address = self._parse_client_ip(request)
            record.last_user_agent = request.headers.get("user-agent")
            record.trusted_until = trusted_until

    def revoke_current_session(self, request: Request) -> None:
        refresh_token = request.cookies.get(self.SESSION_COOKIE_NAME)
        access_token = request.cookies.get(self.ACCESS_COOKIE_NAME)
        if not refresh_token and not access_token:
            return
        now = self._utcnow()

        with get_session() as session:
            session_record = None
            if refresh_token:
                refresh_hash = self._session_token_hash(refresh_token)
                session_record = session.execute(
                    select(UserSession).where(UserSession.session_token_hash == refresh_hash)
                ).scalar_one_or_none()
            if session_record is None and access_token:
                access_hash = self._session_token_hash(access_token)
                session_record = session.execute(
                    select(UserSession).where(UserSession.access_token_hash == access_hash)
                ).scalar_one_or_none()
            if session_record is not None:
                session_record.revoked_at = now

    def revoke_all_user_sessions(self, *, user_id: str) -> None:
        now = self._utcnow()
        with get_session() as session:
            records = session.execute(
                select(UserSession).where(UserSession.user_id == user_id).where(UserSession.revoked_at.is_(None))
            ).scalars().all()
            for record in records:
                record.revoked_at = now


auth_service = AuthService()
