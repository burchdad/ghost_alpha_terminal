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

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail
except Exception:  # pragma: no cover
    sendgrid = None
    Mail = None


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

    def _twilio_client(self) -> "TwilioClient":
        if TwilioClient is None:
            raise HTTPException(status_code=500, detail="Twilio dependency is not installed")
        if not settings.twilio_account_sid or not settings.twilio_auth_token:
            raise HTTPException(status_code=503, detail="Twilio credentials are not configured")
        return TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)

    def send_sms_verify(self, *, phone_number: str) -> None:
        """Send OTP via Twilio Verify (no from-number needed, Twilio manages the code)."""
        if not settings.twilio_verify_service_sid:
            raise HTTPException(status_code=503, detail="TWILIO_VERIFY_SERVICE_SID is not configured")
        try:
            client = self._twilio_client()
            client.verify.v2.services(settings.twilio_verify_service_sid) \
                .verifications.create(to=phone_number, channel="sms")
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to send SMS verification: {exc}") from exc

    def verify_sms_code(self, *, phone_number: str, code: str) -> bool:
        """Check OTP via Twilio Verify VerificationCheck. Returns True if approved."""
        if not settings.twilio_verify_service_sid:
            raise HTTPException(status_code=503, detail="TWILIO_VERIFY_SERVICE_SID is not configured")
        try:
            client = self._twilio_client()
            result = client.verify.v2.services(settings.twilio_verify_service_sid) \
                .verification_checks.create(to=phone_number, code=code)
            return result.status == "approved"
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to verify SMS code: {exc}") from exc

    def send_email_code(self, *, to_email: str, code: str) -> None:
        subject = "Your Ghost Alpha Terminal verification code"
        body = f"Your verification code is {code}. This code expires in {settings.otp_code_ttl_minutes} minutes."

        # Prefer SendGrid when API key is configured
        if settings.sendgrid_api_key:
            try:
                self._send_via_sendgrid(to_email=to_email, subject=subject, body=body)
                return
            except HTTPException:
                # If SendGrid fails but SMTP is available, fall back automatically.
                if settings.smtp_host and settings.smtp_from_email:
                    self._send_via_smtp(to_email=to_email, subject=subject, body=body)
                    return
                raise
        elif settings.smtp_host and settings.smtp_from_email:
            self._send_via_smtp(to_email=to_email, subject=subject, body=body)
        else:
            raise HTTPException(status_code=503, detail="Email provider is not configured")

    def _send_via_sendgrid(self, *, to_email: str, subject: str, body: str) -> None:
        if sendgrid is None or Mail is None:
            raise HTTPException(status_code=500, detail="SendGrid dependency is not installed")
        from_email = settings.sendgrid_from or settings.smtp_from_email
        if not from_email:
            raise HTTPException(status_code=503, detail="SendGrid sender address is not configured")
        try:
            message = Mail(
                from_email=from_email,
                to_emails=to_email,
                subject=subject,
                plain_text_content=body,
            )
            sg = sendgrid.SendGridAPIClient(api_key=settings.sendgrid_api_key.strip())
            response = sg.send(message)
            if response.status_code >= 400:
                raise RuntimeError(f"SendGrid returned HTTP {response.status_code}")
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Failed to send email via SendGrid: {exc}") from exc

    def _send_via_smtp(self, *, to_email: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = settings.smtp_from_email
        msg["To"] = to_email
        msg.set_content(body)

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
            raise HTTPException(status_code=502, detail=f"Failed to send email via SMTP: {exc}") from exc


twofa_service = TwoFAService()
