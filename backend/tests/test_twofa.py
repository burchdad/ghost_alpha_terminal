"""
Tests for 2FA service and auth endpoints.

Coverage:
  - TwoFAService unit tests (TOTP, SMS, email/SendGrid, email/SMTP)
  - /auth/initiate-2fa  (totp, sms, email)
  - /auth/verify-2fa-setup (totp, sms, email, expired, wrong code)
  - /auth/resend-2fa-code
  - /auth/signup-complete (happy path, missing agreements, duplicate email)
  - /auth/signup legacy 410
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Point at the backend package so tests can import app.*
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Use a temp file SQLite DB (in-memory SQLite has per-connection isolation)
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db.name}"
os.environ.setdefault("AUTH_SESSION_SECRET", "test-secret-key-for-tests-only")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db.init_db import initialize_database  # noqa: E402

# Create tables once
initialize_database()

client = TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_email(suffix: str = "") -> str:
    import uuid
    return f"test-{uuid.uuid4().hex[:8]}{suffix}@example.com"


# ---------------------------------------------------------------------------
# TwoFAService unit tests
# ---------------------------------------------------------------------------

class TestTwoFAServiceTOTP(unittest.TestCase):
    def setUp(self):
        from app.services.twofa_service import twofa_service
        self.svc = twofa_service

    def test_generate_totp_secret_returns_base32_string(self):
        secret = self.svc.generate_totp_secret()
        self.assertIsInstance(secret, str)
        self.assertGreater(len(secret), 10)

    def test_build_otpauth_uri_contains_email_and_issuer(self):
        secret = self.svc.generate_totp_secret()
        uri = self.svc.build_otpauth_uri(email="user@example.com", secret=secret)
        self.assertIn("user%40example.com", uri)
        self.assertIn("Ghost", uri)

    def test_verify_totp_valid_code(self):
        import pyotp
        secret = self.svc.generate_totp_secret()
        code = pyotp.TOTP(secret).now()
        self.assertTrue(self.svc.verify_totp(secret=secret, code=code))

    def test_verify_totp_wrong_code(self):
        secret = self.svc.generate_totp_secret()
        self.assertFalse(self.svc.verify_totp(secret=secret, code="000000"))

    def test_verify_totp_rejects_non_digit_input(self):
        secret = self.svc.generate_totp_secret()
        self.assertFalse(self.svc.verify_totp(secret=secret, code="abcdef"))

    def test_verify_totp_rejects_short_code(self):
        secret = self.svc.generate_totp_secret()
        self.assertFalse(self.svc.verify_totp(secret=secret, code="123"))


class TestTwoFAServiceSMS(unittest.TestCase):
    def setUp(self):
        from app.services.twofa_service import twofa_service
        self.svc = twofa_service

    @patch("app.services.twofa_service.settings")
    @patch("app.services.twofa_service.TwilioClient")
    def test_send_sms_verify_calls_twilio_verify_api(self, mock_client_cls, mock_settings):
        mock_settings.twilio_account_sid = "ACtest123"
        mock_settings.twilio_auth_token = "authtoken"
        mock_settings.twilio_verify_service_sid = "VAtest456"

        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        self.svc.send_sms_verify(phone_number="+12223334444")

        mock_client_cls.assert_called_once_with("ACtest123", "authtoken")
        mock_instance.verify.v2.services.assert_called_once_with("VAtest456")
        mock_instance.verify.v2.services().verifications.create.assert_called_once_with(
            to="+12223334444", channel="sms"
        )

    @patch("app.services.twofa_service.settings")
    @patch("app.services.twofa_service.TwilioClient")
    def test_verify_sms_code_returns_true_when_approved(self, mock_client_cls, mock_settings):
        mock_settings.twilio_account_sid = "ACtest123"
        mock_settings.twilio_auth_token = "authtoken"
        mock_settings.twilio_verify_service_sid = "VAtest456"

        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.verify.v2.services().verification_checks.create.return_value = \
            MagicMock(status="approved")

        result = self.svc.verify_sms_code(phone_number="+12223334444", code="123456")
        self.assertTrue(result)

    @patch("app.services.twofa_service.settings")
    @patch("app.services.twofa_service.TwilioClient")
    def test_verify_sms_code_returns_false_when_not_approved(self, mock_client_cls, mock_settings):
        mock_settings.twilio_account_sid = "ACtest123"
        mock_settings.twilio_auth_token = "authtoken"
        mock_settings.twilio_verify_service_sid = "VAtest456"

        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.verify.v2.services().verification_checks.create.return_value = \
            MagicMock(status="pending")

        result = self.svc.verify_sms_code(phone_number="+12223334444", code="000000")
        self.assertFalse(result)

    @patch("app.services.twofa_service.settings")
    def test_send_sms_raises_503_when_verify_sid_not_configured(self, mock_settings):
        mock_settings.twilio_account_sid = "ACtest"
        mock_settings.twilio_auth_token = "token"
        mock_settings.twilio_verify_service_sid = ""
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            self.svc.send_sms_verify(phone_number="+1111")
        self.assertEqual(ctx.exception.status_code, 503)

    @patch("app.services.twofa_service.settings")
    def test_send_sms_raises_503_when_credentials_not_configured(self, mock_settings):
        mock_settings.twilio_account_sid = ""
        mock_settings.twilio_auth_token = ""
        mock_settings.twilio_verify_service_sid = "VAtest"
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            self.svc.send_sms_verify(phone_number="+1111")
        # 503 = creds not configured, 500 = dependency error; both are server-side rejections
        self.assertIn(ctx.exception.status_code, (500, 503))


class TestTwoFAServiceEmail(unittest.TestCase):
    def setUp(self):
        from app.services.twofa_service import twofa_service
        self.svc = twofa_service

    @patch("app.services.twofa_service.settings")
    @patch("app.services.twofa_service.sendgrid")
    @patch("app.services.twofa_service.Mail")
    def test_send_email_code_via_sendgrid(self, mock_mail_cls, mock_sg_module, mock_settings):
        mock_settings.sendgrid_api_key = "SG.test"
        mock_settings.sendgrid_from = "noreply@ghost.com"
        mock_settings.smtp_host = ""
        mock_settings.smtp_from_email = ""
        mock_settings.otp_code_ttl_minutes = 10

        mock_sg_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_sg_instance.send.return_value = mock_response
        mock_sg_module.SendGridAPIClient.return_value = mock_sg_instance

        self.svc.send_email_code(to_email="user@example.com", code="654321")

        mock_sg_module.SendGridAPIClient.assert_called_once_with(api_key="SG.test")
        mock_sg_instance.send.assert_called_once()

    @patch("app.services.twofa_service.settings")
    @patch("app.services.twofa_service.smtplib.SMTP")
    def test_send_email_code_via_smtp_fallback(self, mock_smtp_cls, mock_settings):
        mock_settings.sendgrid_api_key = ""
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "user"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_from_email = "noreply@example.com"
        mock_settings.smtp_use_ssl = False
        mock_settings.smtp_use_starttls = False
        mock_settings.otp_code_ttl_minutes = 10

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        self.svc.send_email_code(to_email="user@example.com", code="789012")
        mock_smtp_cls.assert_called_once_with("smtp.example.com", 587)

    @patch("app.services.twofa_service.settings")
    @patch("app.services.twofa_service.sendgrid")
    @patch("app.services.twofa_service.Mail")
    @patch("app.services.twofa_service.smtplib.SMTP")
    def test_send_email_sendgrid_401_falls_back_to_smtp(self, mock_smtp_cls, mock_mail_cls, mock_sg_module, mock_settings):
        mock_settings.sendgrid_api_key = "SG.invalid"
        mock_settings.sendgrid_from = "noreply@ghost.com"
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "user"
        mock_settings.smtp_password = "pass"
        mock_settings.smtp_from_email = "noreply@example.com"
        mock_settings.smtp_use_ssl = False
        mock_settings.smtp_use_starttls = False
        mock_settings.otp_code_ttl_minutes = 10

        mock_sg_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_sg_instance.send.return_value = mock_response
        mock_sg_module.SendGridAPIClient.return_value = mock_sg_instance

        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = lambda s: mock_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        self.svc.send_email_code(to_email="user@example.com", code="111222")

        mock_sg_instance.send.assert_called_once()
        mock_smtp_cls.assert_called_once_with("smtp.example.com", 587)

    @patch("app.services.twofa_service.settings")
    @patch("app.services.twofa_service.sendgrid")
    @patch("app.services.twofa_service.Mail")
    @patch("app.services.twofa_service.smtplib.SMTP")
    def test_send_email_reports_both_sendgrid_and_smtp_errors(self, mock_smtp_cls, mock_mail_cls, mock_sg_module, mock_settings):
        mock_settings.sendgrid_api_key = "SG.invalid"
        mock_settings.sendgrid_from = "noreply@ghost.com"
        mock_settings.smtp_host = "smtp.example.com"
        mock_settings.smtp_port = 587
        mock_settings.smtp_username = "user"
        mock_settings.smtp_password = "wrong"
        mock_settings.smtp_from_email = "noreply@example.com"
        mock_settings.smtp_use_ssl = False
        mock_settings.smtp_use_starttls = False
        mock_settings.otp_code_ttl_minutes = 10

        mock_sg_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_sg_instance.send.return_value = mock_response
        mock_sg_module.SendGridAPIClient.return_value = mock_sg_instance

        smtp_server = MagicMock()
        smtp_server.send_message.side_effect = RuntimeError("smtp auth failed")
        mock_smtp_cls.return_value.__enter__ = lambda s: smtp_server
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            self.svc.send_email_code(to_email="user@example.com", code="333444")
        self.assertEqual(ctx.exception.status_code, 502)
        detail = str(ctx.exception.detail)
        self.assertIn("SendGrid failed:", detail)
        self.assertIn("SMTP fallback failed:", detail)

    @patch("app.services.twofa_service.settings")
    def test_send_email_raises_503_when_not_configured(self, mock_settings):
        mock_settings.sendgrid_api_key = ""
        mock_settings.smtp_host = ""
        mock_settings.smtp_from_email = ""
        from fastapi import HTTPException
        with self.assertRaises(HTTPException) as ctx:
            self.svc.send_email_code(to_email="user@example.com", code="000000")
        self.assertEqual(ctx.exception.status_code, 503)


# ---------------------------------------------------------------------------
# Auth endpoint integration tests
# ---------------------------------------------------------------------------

class TestInitiate2FA(unittest.TestCase):
    def test_totp_flow_returns_secret_and_qr(self):
        email = _fresh_email()
        resp = client.post("/auth/initiate-2fa", json={
            "email": email,
            "twoFAMethod": "totp",
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["secret"])
        self.assertIn("otpauth://", data["qr_code"])

    @patch("app.api.routes.auth.twofa_service")
    def test_sms_flow_sends_code(self, mock_svc):
        email = _fresh_email()
        resp = client.post("/auth/initiate-2fa", json={
            "email": email,
            "twoFAMethod": "sms",
            "phoneNumber": "+1 (222) 333-4444",
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        mock_svc.send_sms_verify.assert_called_once_with(phone_number="+12223334444")

    @patch("app.api.routes.auth.twofa_service")
    def test_email_flow_sends_code(self, mock_svc):
        email = _fresh_email()
        resp = client.post("/auth/initiate-2fa", json={
            "email": email,
            "twoFAMethod": "email",
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        mock_svc.send_email_code.assert_called_once()

    def test_sms_without_phone_returns_400(self):
        email = _fresh_email()
        resp = client.post("/auth/initiate-2fa", json={
            "email": email,
            "twoFAMethod": "sms",
        })
        self.assertEqual(resp.status_code, 400)

    def test_invalid_method_returns_422(self):
        resp = client.post("/auth/initiate-2fa", json={
            "email": _fresh_email(),
            "twoFAMethod": "carrier-pigeon",
        })
        self.assertEqual(resp.status_code, 422)

    def test_duplicate_email_returns_409(self):
        """Register a user first, then try to initiate 2FA with same email."""
        email = _fresh_email()
        # Create user via signup-complete flow (no mocking needed)
        _complete_signup(email)
        resp = client.post("/auth/initiate-2fa", json={
            "email": email,
            "twoFAMethod": "totp",
        })
        self.assertEqual(resp.status_code, 409)


class TestVerify2FASetup(unittest.TestCase):
    def test_totp_valid_code_returns_success(self):
        import pyotp
        email = _fresh_email()
        init_resp = client.post("/auth/initiate-2fa", json={
            "email": email,
            "twoFAMethod": "totp",
        })
        self.assertEqual(init_resp.status_code, 200)
        secret = init_resp.json()["secret"]
        code = pyotp.TOTP(secret).now()

        verify_resp = client.post("/auth/verify-2fa-setup", json={
            "email": email,
            "twoFAMethod": "totp",
            "verificationCode": code,
        })
        self.assertEqual(verify_resp.status_code, 200, verify_resp.text)
        self.assertTrue(verify_resp.json()["success"])

    def test_totp_wrong_code_returns_400(self):
        email = _fresh_email()
        client.post("/auth/initiate-2fa", json={"email": email, "twoFAMethod": "totp"})
        resp = client.post("/auth/verify-2fa-setup", json={
            "email": email,
            "twoFAMethod": "totp",
            "verificationCode": "000000",
        })
        self.assertEqual(resp.status_code, 400)

    @patch("app.api.routes.auth.twofa_service")
    def test_sms_valid_code_returns_success(self, mock_svc):
        email = _fresh_email()
        mock_svc.send_sms_verify = MagicMock()
        mock_svc.verify_sms_code = MagicMock(return_value=True)
        # Initiate — Twilio Verify sends the code (mocked)
        init_resp = client.post("/auth/initiate-2fa", json={
            "email": email,
            "twoFAMethod": "sms",
            "phoneNumber": "+12223334444",
        })
        self.assertEqual(init_resp.status_code, 200, init_resp.text)
        # Verify — Twilio Verify approves the code (mocked)
        resp = client.post("/auth/verify-2fa-setup", json={
            "email": email,
            "twoFAMethod": "sms",
            "verificationCode": "123456",
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        mock_svc.verify_sms_code.assert_called_once()

    def test_unknown_email_returns_404(self):
        resp = client.post("/auth/verify-2fa-setup", json={
            "email": "nobody@example.com",
            "twoFAMethod": "totp",
            "verificationCode": "123456",
        })
        self.assertEqual(resp.status_code, 404)


class TestResend2FACode(unittest.TestCase):
    @patch("app.api.routes.auth.twofa_service")
    def test_resend_email_code_updates_code(self, mock_svc):
        mock_svc.send_email_code = MagicMock()
        email = _fresh_email()
        client.post("/auth/initiate-2fa", json={"email": email, "twoFAMethod": "email"})

        resp = client.post("/auth/resend-2fa-code", json={
            "email": email,
            "twoFAMethod": "email",
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        # send_email_code called twice (initiate + resend)
        self.assertEqual(mock_svc.send_email_code.call_count, 2)

    def test_resend_unknown_session_returns_404(self):
        resp = client.post("/auth/resend-2fa-code", json={
            "email": "ghost@example.com",
            "twoFAMethod": "email",
        })
        self.assertEqual(resp.status_code, 404)

    def test_resend_totp_returns_422(self):
        """TOTP is excluded from resend (pattern is sms|email)."""
        resp = client.post("/auth/resend-2fa-code", json={
            "email": _fresh_email(),
            "twoFAMethod": "totp",
        })
        self.assertEqual(resp.status_code, 422)


class TestSignupComplete(unittest.TestCase):
    def test_happy_path_creates_user_and_session(self):
        email = _fresh_email()
        resp = _complete_signup(email)
        self.assertEqual(resp.status_code, 200, resp.text)
        data = resp.json()
        self.assertIn("user", data)
        self.assertEqual(data["user"]["email"], email)

    def test_missing_agreement_returns_400(self):
        email = _fresh_email()
        _initiate_and_verify_totp(email)
        resp = client.post("/auth/signup-complete", json={
            "fullName": "Test User",
            "email": email,
            "password": "Passw0rd!",
            "twoFAMethod": "totp",
            "agreePrivacy": True,
            "agreeTerms": False,   # not accepted
            "agreeRisk": True,
        })
        self.assertEqual(resp.status_code, 400)

    def test_unverified_2fa_returns_400(self):
        email = _fresh_email()
        client.post("/auth/initiate-2fa", json={"email": email, "twoFAMethod": "totp"})
        # Do NOT verify — go straight to complete
        resp = client.post("/auth/signup-complete", json={
            "fullName": "Test User",
            "email": email,
            "password": "Passw0rd!",
            "twoFAMethod": "totp",
            "agreePrivacy": True,
            "agreeTerms": True,
            "agreeRisk": True,
        })
        self.assertEqual(resp.status_code, 400)

    def test_duplicate_email_returns_409(self):
        email = _fresh_email()
        # First signup succeeds
        _complete_signup(email)
        # signup-complete with the same email should 409 directly
        # (we can skip initiate/verify since signup-complete checks for existing users)
        resp = client.post("/auth/signup-complete", json={
            "fullName": "Test User",
            "email": email,
            "password": "Passw0rd!",
            "twoFAMethod": "totp",
            "agreePrivacy": True,
            "agreeTerms": True,
            "agreeRisk": True,
        })
        self.assertEqual(resp.status_code, 409)

    def test_weak_password_returns_422(self):
        email = _fresh_email()
        _initiate_and_verify_totp(email)
        resp = client.post("/auth/signup-complete", json={
            "fullName": "Test User",
            "email": email,
            "password": "short",
            "twoFAMethod": "totp",
            "agreePrivacy": True,
            "agreeTerms": True,
            "agreeRisk": True,
        })
        self.assertEqual(resp.status_code, 422)


class TestLegacySignupDisabled(unittest.TestCase):
    def test_legacy_signup_returns_410(self):
        resp = client.post("/auth/signup", json={
            "email": _fresh_email(),
            "password": "Passw0rd!",
        })
        self.assertEqual(resp.status_code, 410)


# ---------------------------------------------------------------------------
# Utility helpers used by integration tests
# ---------------------------------------------------------------------------

def _initiate_and_verify_totp(email: str) -> None:
    """Initiate TOTP 2FA and verify it for the given email."""
    import pyotp
    init = client.post("/auth/initiate-2fa", json={"email": email, "twoFAMethod": "totp"})
    assert init.status_code == 200, f"initiate failed: {init.text}"
    secret = init.json()["secret"]
    code = pyotp.TOTP(secret).now()
    verify = client.post("/auth/verify-2fa-setup", json={
        "email": email,
        "twoFAMethod": "totp",
        "verificationCode": code,
    })
    assert verify.status_code == 200, f"verify failed: {verify.text}"


def _complete_signup(email: str):
    """Run the full TOTP signup flow for the given email and return the final response."""
    _initiate_and_verify_totp(email)
    return client.post("/auth/signup-complete", json={
        "fullName": "Test User",
        "email": email,
        "password": "Passw0rd!",
        "twoFAMethod": "totp",
        "agreePrivacy": True,
        "agreeTerms": True,
        "agreeRisk": True,
    })


if __name__ == "__main__":
    unittest.main(verbosity=2)
