from __future__ import annotations

import smtplib
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage

from fastapi import HTTPException

from app.core.config import settings

try:
    import pyotp
except Exception:  # pragma: no cover
    pyotp = None

try:
    from twilio.rest import Client as TwilioClient
except Exception:  # pragma: no cover
    TwilioClient = None


class TwoFAService:
    def _utcnow(self) -> datetime:
        return datetime.now(tz=timezone.utc)

    def generate_totp_secret(self) -> str:
        if pyotp is None:
            raise HTTPException(status_code=500, detail="TOTP dependency is not installed")
        return pyotp.random_base32()

    def build_otpauth_uri(self, *, email: str, secret: str) -> str:
        if pyotp is None:
            raise HTTPException(status_code=500, detail="TOTP dependency is not installed")
        issuer = settings.twofa_totp_issuer or "Ghost Alpha Terminal"
        return pyotp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer)

    def verify_totp(self, *, secret: str, code: str) -> bool:
        if pyotp is None:
            raise HTTPException(status_code=500, detail="TOTP dependency is not installed")
        candidate = str(code or "").strip()
        if len(candidate) != 6 or not candidate.isdigit():
            return False
        totp = pyotp.TOTP(secret)
        return bool(totp.verify(candidate, valid_window=1))

    def send_sms_code(self, *, phone_number: str, code: str) -> None:
        if not settings.twilio_account_sid or not settings.twilio_auth_token or not settings.twilio_from_number:
            raise HTTPException(status_code=503, detail="SMS provider is not configured")
        if TwilioClient is None:
            raise HTTPException(status_code=500, detail="Twilio dependency is not installed")

        body = f"Your Ghost Alpha Terminal verification code is {code}. It expires in {settings.otp_code_ttl_minutes} minutes."
        try:
            client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
            client.messages.create(
                body=body,
                from_=settings.twilio_from_number,
                to=phone_number,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to send SMS code: {exc}") from exc

    def send_email_code(self, *, to_email: str, code: str) -> None:
        if not settings.smtp_host or not settings.smtp_from_email:
            raise HTTPException(status_code=503, detail="Email provider is not configured")

        msg = EmailMessage()
        msg["Subject"] = "Your Ghost Alpha Terminal verification code"
        msg["From"] = settings.smtp_from_email
        msg["To"] = to_email
        msg.set_content(
            f"Your verification code is {code}. This code expires in {settings.otp_code_ttl_minutes} minutes."
        )

        try:
            if settings.smtp_use_ssl:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, context=context) as server:
                    if settings.smtp_username:
                        server.login(settings.smtp_username, settings.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                    if settings.smtp_use_starttls:
                        server.starttls(context=ssl.create_default_context())
                    if settings.smtp_username:
                        server.login(settings.smtp_username, settings.smtp_password)
                    server.send_message(msg)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to send email code: {exc}") from exc


twofa_service = TwoFAService()
