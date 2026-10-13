from __future__ import annotations

import smtplib
import ssl

import httpx
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
    def _is_configured(self, value: str | None) -> bool:
        normalized = str(value or "").strip().lower()
        return normalized not in {"", "none", "null"}

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
        if not self._is_configured(settings.twilio_account_sid) or not self._is_configured(settings.twilio_auth_token):
            raise HTTPException(status_code=503, detail="Twilio credentials are not configured")
        return TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)

    def send_sms_verify(self, *, phone_number: str) -> None:
        """Send OTP via Twilio Verify (no from-number needed, Twilio manages the code)."""
        if not self._is_configured(settings.twilio_verify_service_sid):
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
        if not self._is_configured(settings.twilio_verify_service_sid):
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

        # Prefer Resend when API key is configured
        if self._is_configured(settings.resend_api_key):
            try:
                self._send_via_resend(to_email=to_email, subject=subject, body=body)
                return
            except HTTPException as resend_exc:
                # If Resend fails but SMTP is available, fall back automatically.
                if self._is_configured(settings.smtp_host) and self._is_configured(settings.smtp_from_email):
                    try:
                        self._send_via_smtp(to_email=to_email, subject=subject, body=body)
                        return
                    except HTTPException as smtp_exc:
                        raise HTTPException(
                            status_code=502,
                            detail=(
                                f"Resend failed: {resend_exc.detail}; "
                                f"SMTP fallback failed: {smtp_exc.detail}"
                            ),
                        ) from smtp_exc
                raise resend_exc
        elif self._is_configured(settings.smtp_host) and self._is_configured(settings.smtp_from_email):
            self._send_via_smtp(to_email=to_email, subject=subject, body=body)
        else:
            raise HTTPException(status_code=503, detail="Email provider is not configured")

    def send_security_alert(
        self,
        *,
        to_email: str,
        method: str,
        ip_address: str | None,
        device: str | None,
        location: str | None = None,
        event: str = "New login detected",
    ) -> None:
        subject = "Ghost Alpha Terminal security alert"
        details = [
            f"Event: {event}",
            f"2FA method: {method}",
            f"IP address: {ip_address or 'unknown'}",
            f"Device: {device or 'unknown'}",
        ]
        if location:
            details.append(f"Location: {location}")
        body = "\n".join(details)

        try:
            if self._is_configured(settings.resend_api_key):
                self._send_via_resend(to_email=to_email, subject=subject, body=body)
            elif self._is_configured(settings.smtp_host) and self._is_configured(settings.smtp_from_email):
                self._send_via_smtp(to_email=to_email, subject=subject, body=body)
        except Exception:
            # Alerts should never block auth/session flow.
            return

    def send_password_reset_email(self, *, to_email: str, reset_link: str) -> None:
        subject = "Reset your Ghost Alpha Terminal password"
        body = (
            "We received a request to reset your password.\n\n"
            f"Reset link: {reset_link}\n\n"
            f"This link expires in {settings.password_reset_ttl_minutes} minutes. "
            "If you did not request this, you can safely ignore this email."
        )

        if self._is_configured(settings.resend_api_key):
            self._send_via_resend(to_email=to_email, subject=subject, body=body)
            return
        if self._is_configured(settings.smtp_host) and self._is_configured(settings.smtp_from_email):
            self._send_via_smtp(to_email=to_email, subject=subject, body=body)
            return
        raise HTTPException(status_code=503, detail="Email provider is not configured")

    def send_withdrawal_approval_email(
        self,
        *,
        to_email: str,
        amount: float,
        destination: str,
        confirm_link: str,
        deny_link: str,
        hold_minutes: int,
    ) -> None:
        subject = "Confirm or deny your withdrawal request"
        body = (
            "A withdrawal request is currently held pending your approval.\n\n"
            f"Amount: {amount:.2f}\n"
            f"Destination: {destination}\n"
            f"Hold window: {hold_minutes} minutes\n\n"
            f"Confirm: {confirm_link}\n"
            f"Deny: {deny_link}\n\n"
            "If this was not you, deny immediately and rotate credentials."
        )

        if self._is_configured(settings.resend_api_key):
            self._send_via_resend(to_email=to_email, subject=subject, body=body)
            return
        if self._is_configured(settings.smtp_host) and self._is_configured(settings.smtp_from_email):
            self._send_via_smtp(to_email=to_email, subject=subject, body=body)
            return
        raise HTTPException(status_code=503, detail="Email provider is not configured")

    def _send_via_resend(self, *, to_email: str, subject: str, body: str) -> None:
        api_key = str(settings.resend_api_key or "").strip()
        if not self._is_configured(api_key):
            raise HTTPException(status_code=503, detail="Resend API key is not configured")
        from_email = str(settings.resend_from or settings.smtp_from_email or "").strip()
        if not self._is_configured(from_email):
            raise HTTPException(status_code=503, detail="Resend sender address is not configured")
        try:
            response = httpx.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "from": from_email,
                    "to": [to_email],
                    "subject": subject,
                    "text": body,
                },
                timeout=15.0,
                follow_redirects=False,
            )
            response.raise_for_status()
            result = response.json()
            if not isinstance(result, dict) or not isinstance(result.get("id"), str) or not result["id"].strip():
                raise ValueError("Resend did not acknowledge the email")
        except httpx.HTTPStatusError as exc:
            # Never expose provider response bodies, email contents, or credentials.
            raise HTTPException(
                status_code=502,
                detail=f"Failed to send email via Resend (HTTP {exc.response.status_code})",
            ) from exc
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Failed to send email via Resend") from exc

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
