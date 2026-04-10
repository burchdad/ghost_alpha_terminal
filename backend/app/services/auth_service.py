from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, Request, Response
from sqlalchemy import select

from app.core.config import settings
from app.db.models import User, UserSession
from app.db.session import get_session


class AuthService:
    SESSION_COOKIE_NAME = "ghost_auth_session"
    SESSION_TTL_DAYS = 14
    PASSWORD_ITERATIONS = 210_000

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

    def _cookie_secure(self) -> bool:
        return bool(settings.auth_cookie_secure)

    def _cookie_samesite(self) -> str:
        value = str(settings.auth_cookie_samesite or "lax").lower().strip()
        if value not in {"lax", "strict", "none"}:
            return "lax"
        return value

    def create_user(self, *, email: str, password: str) -> User:
        normalized_email = self._normalize_email(email)
        if not normalized_email:
            raise HTTPException(status_code=400, detail="Email is required")
        if len(password) < 8:
            raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

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

    def _create_session(self, *, user_id: str, request: Request) -> str:
        session_token = secrets.token_urlsafe(48)
        token_hash = self._session_token_hash(session_token)
        now = self._utcnow()
        expires_at = now + timedelta(days=self.SESSION_TTL_DAYS)

        with get_session() as session:
            record = UserSession(
                user_id=user_id,
                session_token_hash=token_hash,
                user_agent=request.headers.get("user-agent"),
                ip_address=request.client.host if request.client else None,
                expires_at=expires_at,
                created_at=now,
                revoked_at=None,
            )
            session.add(record)

        return session_token

    def issue_login_cookie(self, *, response: Response, user_id: str, request: Request) -> None:
        session_token = self._create_session(user_id=user_id, request=request)
        max_age = int(timedelta(days=self.SESSION_TTL_DAYS).total_seconds())
        response.set_cookie(
            key=self.SESSION_COOKIE_NAME,
            value=session_token,
            httponly=True,
            secure=self._cookie_secure(),
            samesite=self._cookie_samesite(),
            max_age=max_age,
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

    def get_current_user(self, request: Request) -> User:
        raw_token = request.cookies.get(self.SESSION_COOKIE_NAME)
        if not raw_token:
            raise HTTPException(status_code=401, detail="Authentication required")

        token_hash = self._session_token_hash(raw_token)
        now = self._utcnow()

        with get_session() as session:
            row = session.execute(
                select(UserSession, User)
                .join(User, User.id == UserSession.user_id)
                .where(UserSession.session_token_hash == token_hash)
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
            if not bool(user.is_active):
                raise HTTPException(status_code=403, detail="User is inactive")

            return user

    def revoke_current_session(self, request: Request) -> None:
        raw_token = request.cookies.get(self.SESSION_COOKIE_NAME)
        if not raw_token:
            return
        token_hash = self._session_token_hash(raw_token)
        now = self._utcnow()

        with get_session() as session:
            session_record = session.execute(
                select(UserSession).where(UserSession.session_token_hash == token_hash)
            ).scalar_one_or_none()
            if session_record is not None:
                session_record.revoked_at = now


auth_service = AuthService()
