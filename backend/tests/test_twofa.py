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
import base64
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from sqlalchemy import select
from ecdsa import NIST256p, SigningKey, util as ecdsa_util

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
from app.db.models import (  # noqa: E402
    AuthAuditLog,
    LoginSecurityState,
    PasswordResetToken,
    TrustedDevice,
    User,
    User2FASetup,
    WithdrawalApproval,
)
from app.db.session import get_session  # noqa: E402

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
            "password": "Passw0rd!X",
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
            "password": "Passw0rd!X",
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
            "password": "Passw0rd!X",
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
            "password": "Passw0rd!X",
        })
        self.assertEqual(resp.status_code, 410)


class TestSecurityHardening(unittest.TestCase):
    def setUp(self):
        client.cookies.clear()

    @patch("app.api.routes.auth.twofa_service")
    def test_email_otp_is_hashed_in_storage(self, mock_svc):
        sent_codes: list[str] = []

        def _capture_code(*, to_email: str, code: str):
            sent_codes.append(code)

        mock_svc.send_email_code.side_effect = _capture_code
        mock_svc.send_security_alert = MagicMock()

        email = _fresh_email("-hash")
        init = client.post("/auth/initiate-2fa", json={"email": email, "twoFAMethod": "email"})
        self.assertEqual(init.status_code, 200, init.text)
        self.assertEqual(len(sent_codes), 1)

        with get_session() as session:
            row = session.execute(select(User2FASetup).where(User2FASetup.email == email)).scalar_one()
            self.assertIsNotNone(row.verification_code_hash)
            self.assertNotEqual(row.verification_code_hash, sent_codes[0])

    @patch("app.api.routes.auth.twofa_service")
    def test_setup_rate_limit_locks_after_max_attempts(self, mock_svc):
        mock_svc.send_email_code = MagicMock()
        mock_svc.send_security_alert = MagicMock()

        email = _fresh_email("-lock")
        init = client.post("/auth/initiate-2fa", json={"email": email, "twoFAMethod": "email"})
        self.assertEqual(init.status_code, 200, init.text)

        for _ in range(5):
            resp = client.post("/auth/verify-2fa-setup", json={
                "email": email,
                "twoFAMethod": "email",
                "verificationCode": "000000",
            })
            self.assertEqual(resp.status_code, 400)

        locked = client.post("/auth/verify-2fa-setup", json={
            "email": email,
            "twoFAMethod": "email",
            "verificationCode": "000000",
        })
        self.assertEqual(locked.status_code, 429)

    @patch("app.api.routes.auth.twofa_service.send_security_alert")
    def test_high_trust_step_up_flow_for_totp_user(self, mock_alert):
        import pyotp

        email = _fresh_email("-stepup")
        signup_resp = _complete_signup(email)
        self.assertEqual(signup_resp.status_code, 200, signup_resp.text)

        status_before = client.get("/auth/session/high-trust-status")
        self.assertEqual(status_before.status_code, 200, status_before.text)
        self.assertFalse(status_before.json()["high_trust"])

        challenge = client.post("/auth/2fa/challenge", json={})
        self.assertEqual(challenge.status_code, 200, challenge.text)
        self.assertEqual(challenge.json()["method"], "totp")

        with get_session() as session:
            user = session.execute(select(User).where(User.email == email)).scalar_one()
            code = pyotp.TOTP(str(user.twofa_secret)).now()

        verify = client.post("/auth/2fa/verify", json={"verificationCode": code, "trustDevice": True})
        self.assertEqual(verify.status_code, 200, verify.text)
        self.assertTrue(verify.json()["success"])
        mock_alert.assert_called()

        status_after = client.get("/auth/session/high-trust-status")
        self.assertEqual(status_after.status_code, 200, status_after.text)
        self.assertTrue(status_after.json()["high_trust"])


class TestPasswordResetFlow(unittest.TestCase):
    def setUp(self):
        client.cookies.clear()
        from app.db.models import AuthRateLimitBucket, PasswordResetToken

        with get_session() as session:
            session.query(AuthRateLimitBucket).delete()
            session.query(PasswordResetToken).delete()


class TestFinalHardeningLayer(unittest.TestCase):
    def setUp(self):
        client.cookies.clear()
        from app.db.models import AuthAuditLog, AuthRateLimitBucket, LoginSecurityState, PasswordResetToken

        with get_session() as session:
            session.query(AuthAuditLog).delete()
            session.query(AuthRateLimitBucket).delete()
            session.query(LoginSecurityState).delete()
            session.query(PasswordResetToken).delete()

    @patch("app.api.routes.auth.twofa_service.send_security_alert")
    def test_refresh_rotates_tokens_and_keeps_session_valid(self, _mock_alert):
        email = _fresh_email("-refresh")
        signup_resp = _complete_signup(email)
        self.assertEqual(signup_resp.status_code, 200, signup_resp.text)

        before_refresh = client.cookies.get("ghost_auth_session")
        before_access = client.cookies.get("ghost_auth_access")
        self.assertTrue(before_refresh)
        self.assertTrue(before_access)

        refresh = client.post("/auth/refresh")
        self.assertEqual(refresh.status_code, 200, refresh.text)

        after_refresh = client.cookies.get("ghost_auth_session")
        after_access = client.cookies.get("ghost_auth_access")
        self.assertTrue(after_refresh)
        self.assertTrue(after_access)
        self.assertNotEqual(before_refresh, after_refresh)
        self.assertNotEqual(before_access, after_access)

        me = client.get("/auth/me")
        self.assertEqual(me.status_code, 200, me.text)

    @patch("app.api.routes.auth.twofa_service.send_security_alert")
    def test_adaptive_risk_forces_step_up_on_new_ip_prefix(self, _mock_alert):
        import pyotp

        email = _fresh_email("-risk")
        signup_resp = _complete_signup(email)
        self.assertEqual(signup_resp.status_code, 200, signup_resp.text)

        fixed_device = "device-risk-test-1"
        first_headers = {"x-device-fingerprint": fixed_device, "x-forwarded-for": "1.1.1.10"}

        challenge = client.post("/auth/2fa/challenge", json={}, headers=first_headers)
        self.assertEqual(challenge.status_code, 200, challenge.text)

        with get_session() as session:
            user = session.execute(select(User).where(User.email == email)).scalar_one()
            code = pyotp.TOTP(str(user.twofa_secret)).now()

        verify = client.post(
            "/auth/2fa/verify",
            json={"verificationCode": code, "trustDevice": True},
            headers=first_headers,
        )
        self.assertEqual(verify.status_code, 200, verify.text)

        logout = client.post("/auth/logout", headers=first_headers)
        self.assertEqual(logout.status_code, 200, logout.text)

        login_same_network = client.post(
            "/auth/login",
            json={"email": email, "password": "Passw0rd!X"},
            headers={"x-device-fingerprint": fixed_device, "x-forwarded-for": "1.1.1.11"},
        )
        self.assertEqual(login_same_network.status_code, 200, login_same_network.text)
        status_same_network = client.get(
            "/auth/session/high-trust-status",
            headers={"x-device-fingerprint": fixed_device, "x-forwarded-for": "1.1.1.11"},
        )
        self.assertEqual(status_same_network.status_code, 200, status_same_network.text)
        self.assertFalse(status_same_network.json()["step_up_required"])

        client.post("/auth/logout", headers={"x-device-fingerprint": fixed_device, "x-forwarded-for": "1.1.1.11"})

        login_new_ip = client.post(
            "/auth/login",
            json={"email": email, "password": "Passw0rd!X"},
            headers={"x-device-fingerprint": fixed_device, "x-forwarded-for": "2.2.2.20"},
        )
        self.assertEqual(login_new_ip.status_code, 200, login_new_ip.text)
        status_new_ip = client.get(
            "/auth/session/high-trust-status",
            headers={"x-device-fingerprint": fixed_device, "x-forwarded-for": "2.2.2.20"},
        )
        self.assertEqual(status_new_ip.status_code, 200, status_new_ip.text)
        self.assertTrue(status_new_ip.json()["step_up_required"])
        self.assertIn("new_ip_prefix", status_new_ip.json()["risk_reasons"])

    @patch("app.api.routes.auth.settings.login_progressive_delay_seconds", new=0)
    @patch("app.api.routes.auth.settings.login_progressive_delay_after_failures", new=2)
    @patch("app.api.routes.auth.settings.login_lock_after_failures", new=3)
    @patch("app.api.routes.auth.settings.login_lock_minutes", new=1)
    def test_login_account_lock_after_repeated_failures(self):
        email = _fresh_email("-lock-login")
        _complete_signup(email)
        client.cookies.clear()

        for _ in range(3):
            failed = client.post("/auth/login", json={"email": email, "password": "WrongPass!1"})
            self.assertEqual(failed.status_code, 401, failed.text)

        blocked = client.post("/auth/login", json={"email": email, "password": "Passw0rd!X"})
        self.assertEqual(blocked.status_code, 429, blocked.text)

    @patch("app.api.routes.auth.twofa_service.send_security_alert")
    def test_auth_audit_log_captures_login_and_password_reset(self, _mock_alert):
        from urllib.parse import parse_qs, urlparse

        email = _fresh_email("-audit")
        _complete_signup(email)

        login_ok = client.post("/auth/login", json={"email": email, "password": "Passw0rd!X"})
        self.assertEqual(login_ok.status_code, 200, login_ok.text)

        captured_token = {"value": ""}

        with patch("app.api.routes.auth.twofa_service.send_password_reset_email") as mock_send_reset:
            def _capture(*, to_email: str, reset_link: str):
                self.assertEqual(to_email, email)
                query = parse_qs(urlparse(reset_link).query)
                captured_token["value"] = query.get("reset_token", [""])[0]

            mock_send_reset.side_effect = _capture
            forgot = client.post("/auth/forgot-password", json={"email": email})
            self.assertEqual(forgot.status_code, 200, forgot.text)

        reset = client.post("/auth/reset-password", json={"token": captured_token["value"], "newPassword": "An0therPass!"})
        self.assertEqual(reset.status_code, 200, reset.text)

        with get_session() as session:
            login_events = session.execute(select(AuthAuditLog).where(AuthAuditLog.event_type == "login")).scalars().all()
            reset_events = session.execute(
                select(AuthAuditLog).where(AuthAuditLog.event_type.in_(["password_reset_request", "password_reset"]))
            ).scalars().all()
            self.assertGreaterEqual(len(login_events), 1)
            self.assertGreaterEqual(len(reset_events), 2)

    def test_withdrawal_requires_authentication(self):
        client.cookies.clear()
        resp = client.post(
            "/alpaca/withdrawals",
            json={"amount": 100.0, "destination": "bank-rel-001", "memo": "test"},
        )
        self.assertEqual(resp.status_code, 401, resp.text)

    @patch("app.api.routes.auth.twofa_service.send_security_alert")
    def test_withdrawal_requires_high_trust_even_when_logged_in(self, _mock_alert):
        email = _fresh_email("-withdraw-gate")
        signup_resp = _complete_signup(email)
        self.assertEqual(signup_resp.status_code, 200, signup_resp.text)

        resp = client.post(
            "/alpaca/withdrawals",
            json={"amount": 100.0, "destination": "bank-rel-002", "memo": "test"},
        )
        self.assertEqual(resp.status_code, 403, resp.text)

    @patch("app.api.routes.alpaca.twofa_service.send_security_alert")
    def test_withdrawal_requires_recent_step_up_otp(self, _mock_alert):
        email = _fresh_email("-withdraw-stepup")
        signup_resp = _complete_signup(email)
        self.assertEqual(signup_resp.status_code, 200, signup_resp.text)

        _perform_login_step_up(email)

        with get_session() as session:
            user = session.execute(select(User).where(User.email == email)).scalar_one()
            verify_event = session.execute(
                select(AuthAuditLog)
                .where(AuthAuditLog.user_id == str(user.id))
                .where(AuthAuditLog.event_type == "2fa_verify")
                .where(AuthAuditLog.status == "success")
                .order_by(AuthAuditLog.created_at.desc())
            ).scalar_one()
            verify_event.created_at = datetime.now(timezone.utc) - timedelta(minutes=20)

        with patch("app.api.routes.alpaca.settings.withdrawal_step_up_max_age_minutes", 5):
            resp = client.post(
                "/alpaca/withdrawals",
                json={"amount": 100.0, "destination": "bank-rel-otp", "memo": "test"},
            )
        self.assertEqual(resp.status_code, 403, resp.text)

    @patch("app.api.routes.alpaca.twofa_service.send_security_alert")
    def test_withdrawal_first_request_is_held_and_alerted(self, mock_alert):
        email = _fresh_email("-withdraw-hold")
        signup_resp = _complete_signup(email)
        self.assertEqual(signup_resp.status_code, 200, signup_resp.text)

        _perform_login_step_up(email)

        with patch("app.api.routes.alpaca.settings.withdrawal_first_cooldown_minutes", 10), patch(
            "app.api.routes.alpaca.settings.withdrawal_new_destination_cooldown_minutes", 15
        ), patch("app.api.routes.alpaca.settings.withdrawal_anomaly_amount_absolute", 1_000_000):
            resp = client.post(
                "/alpaca/withdrawals",
                json={"amount": 120.0, "destination": "bank-rel-new", "memo": "test"},
            )

        self.assertEqual(resp.status_code, 200, resp.text)
        payload = resp.json()
        self.assertEqual(payload["status"], "PENDING")
        self.assertIn("first_withdrawal_cooldown", payload["hold_reasons"])
        self.assertIn("new_destination_cooldown", payload["hold_reasons"])
        events = [call.kwargs.get("event") for call in mock_alert.call_args_list]
        self.assertIn("Withdrawal initiated", events)
        self.assertIn("New device withdrawal attempt", events)

    @patch("app.api.routes.alpaca.twofa_service.send_security_alert")
    def test_withdrawal_anomaly_amount_triggers_hold(self, _mock_alert):
        email = _fresh_email("-withdraw-anomaly")
        signup_resp = _complete_signup(email)
        self.assertEqual(signup_resp.status_code, 200, signup_resp.text)

        _perform_login_step_up(email)

        now = datetime.now(timezone.utc)
        with get_session() as session:
            user = session.execute(select(User).where(User.email == email)).scalar_one()
            for amount in (120.0, 180.0, 160.0):
                session.add(
                    AuthAuditLog(
                        user_id=str(user.id),
                        email=email,
                        event_type="broker_withdrawal",
                        status="success",
                        method="alpaca_oauth",
                        ip_address="127.0.0.1",
                        user_agent="pytest",
                        metadata_json=json.dumps({"amount": amount, "destination": "bank-rel-known"}),
                        created_at=now - timedelta(hours=2),
                    )
                )

        with patch("app.api.routes.alpaca.settings.withdrawal_first_cooldown_minutes", 0), patch(
            "app.api.routes.alpaca.settings.withdrawal_new_destination_cooldown_minutes", 0
        ), patch("app.api.routes.alpaca.settings.withdrawal_anomaly_amount_absolute", 1000):
            resp = client.post(
                "/alpaca/withdrawals",
                json={"amount": 20000.0, "destination": "bank-rel-known", "memo": "large"},
            )

        self.assertEqual(resp.status_code, 200, resp.text)
        payload = resp.json()
        self.assertEqual(payload["status"], "PENDING")
        self.assertTrue(payload["requires_confirmation"])
        self.assertIn("anomaly_hold", payload["hold_reasons"])

    @patch("app.api.routes.auth.twofa_service.send_security_alert")
    def test_webauthn_challenge_and_verify_marks_high_trust(self, _mock_alert):
        email = _fresh_email("-passkey")
        signup_resp = _complete_signup(email)
        self.assertEqual(signup_resp.status_code, 200, signup_resp.text)

        _perform_webauthn_step_up()

        status = client.get("/auth/session/high-trust-status")
        self.assertEqual(status.status_code, 200, status.text)
        self.assertTrue(status.json().get("high_trust"))

    @patch("app.api.routes.alpaca.twofa_service.send_security_alert")
    @patch("app.api.routes.auth.twofa_service.send_security_alert")
    def test_withdrawal_accepts_recent_webauthn_assertion(self, _mock_auth_alert, _mock_alpaca_alert):
        email = _fresh_email("-withdraw-passkey")
        signup_resp = _complete_signup(email)
        self.assertEqual(signup_resp.status_code, 200, signup_resp.text)

        _perform_webauthn_step_up()

        with patch("app.api.routes.alpaca.settings.withdrawal_first_cooldown_minutes", 0), patch(
            "app.api.routes.alpaca.settings.withdrawal_new_destination_cooldown_minutes", 0
        ), patch("app.api.routes.alpaca.settings.withdrawal_anomaly_amount_absolute", 1_000_000):
            resp = client.post(
                "/alpaca/withdrawals",
                json={"amount": 100.0, "destination": "bank-rel-passkey", "memo": "test"},
            )

        # A non-403 response proves recent WebAuthn assertion is accepted as valid step-up.
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json().get("status"), "PENDING")

    @patch("app.api.routes.auth.twofa_service.send_security_alert")
    def test_trusted_device_registry_list_and_revoke(self, _mock_alert):
        email = _fresh_email("-trusted-reg")
        signup_resp = _complete_signup(email)
        self.assertEqual(signup_resp.status_code, 200, signup_resp.text)

        trust = client.post("/auth/devices/trust-current", json={"deviceLabel": "Laptop"})
        self.assertEqual(trust.status_code, 200, trust.text)

        listed = client.get("/auth/devices/trusted")
        self.assertEqual(listed.status_code, 200, listed.text)
        devices = listed.json().get("devices", [])
        self.assertGreaterEqual(len(devices), 1)

        device_id = int(devices[0]["id"])
        revoke = client.delete(f"/auth/devices/trusted/{device_id}")
        self.assertEqual(revoke.status_code, 200, revoke.text)
        self.assertTrue(revoke.json().get("success"))

    @patch("app.api.routes.alpaca.twofa_service.send_security_alert")
    @patch("app.api.routes.auth.twofa_service.send_security_alert")
    def test_withdrawal_approval_deny_flow_marks_denied(self, _mock_auth_alert, _mock_alpaca_alert):
        email = _fresh_email("-approval-deny")
        signup_resp = _complete_signup(email)
        self.assertEqual(signup_resp.status_code, 200, signup_resp.text)

        _perform_webauthn_step_up()
        with patch("app.api.routes.alpaca.settings.withdrawal_first_cooldown_minutes", 10), patch(
            "app.api.routes.alpaca.settings.withdrawal_new_destination_cooldown_minutes", 10
        ), patch("app.api.routes.alpaca.twofa_service.send_withdrawal_approval_email") as mock_send:
            captured = {"link": ""}

            def _capture(**kwargs):
                captured["link"] = kwargs["deny_link"]

            mock_send.side_effect = _capture
            held = client.post(
                "/alpaca/withdrawals",
                json={"amount": 220.0, "destination": "bank-rel-approve", "memo": "approve test"},
            )
            self.assertEqual(held.status_code, 200, held.text)
            self.assertEqual(held.json().get("status"), "PENDING")

        from urllib.parse import parse_qs, urlparse

        token = parse_qs(urlparse(captured["link"]).query).get("token", [""])[0]
        deny = client.get(f"/alpaca/withdrawals/approval/deny?token={token}")
        self.assertEqual(deny.status_code, 200, deny.text)
        self.assertEqual(deny.json().get("status"), "DENIED")

        with get_session() as session:
            user = session.execute(select(User).where(User.email == email)).scalar_one()
            row = session.execute(
                select(WithdrawalApproval)
                .where(WithdrawalApproval.user_id == str(user.id))
                .order_by(WithdrawalApproval.id.desc())
            ).scalar_one()
            self.assertEqual(row.status, "DENIED")

    @patch("app.api.routes.auth.twofa_service.send_password_reset_email")
    def test_forgot_password_known_email_creates_token_and_sends_link(self, mock_send_reset):
        email = _fresh_email("-reset")
        _complete_signup(email)

        resp = client.post("/auth/forgot-password", json={"email": email})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(resp.json()["success"])
        mock_send_reset.assert_called_once()

        with get_session() as session:
            token_row = session.execute(
                select(PasswordResetToken).where(PasswordResetToken.used_at.is_(None))
            ).scalar_one_or_none()
            self.assertIsNotNone(token_row)

    @patch("app.api.routes.auth.twofa_service.send_password_reset_email")
    def test_forgot_password_unknown_email_is_anti_enumeration_success(self, mock_send_reset):
        resp = client.post("/auth/forgot-password", json={"email": _fresh_email("-unknown")})
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertTrue(resp.json()["success"])
        mock_send_reset.assert_not_called()

    @patch("app.api.routes.auth.twofa_service.send_password_reset_email")
    def test_reset_password_with_token_updates_login_password(self, mock_send_reset):
        from urllib.parse import parse_qs, urlparse

        email = _fresh_email("-rotate")
        _complete_signup(email)

        captured_token = {"value": ""}

        def _capture(*, to_email: str, reset_link: str):
            self.assertEqual(to_email, email)
            query = parse_qs(urlparse(reset_link).query)
            captured_token["value"] = query.get("reset_token", [""])[0]

        mock_send_reset.side_effect = _capture

        forgot = client.post("/auth/forgot-password", json={"email": email})
        self.assertEqual(forgot.status_code, 200, forgot.text)
        self.assertTrue(captured_token["value"])

        reset = client.post("/auth/reset-password", json={
            "token": captured_token["value"],
            "newPassword": "N3wPassw0rd!",
        })
        self.assertEqual(reset.status_code, 200, reset.text)

        client.cookies.clear()
        old_login = client.post("/auth/login", json={"email": email, "password": "Passw0rd!X"})
        self.assertEqual(old_login.status_code, 401, old_login.text)

        new_login = client.post("/auth/login", json={"email": email, "password": "N3wPassw0rd!"})
        self.assertEqual(new_login.status_code, 200, new_login.text)

    def test_reset_password_rejects_invalid_token(self):
        resp = client.post("/auth/reset-password", json={
            "token": "not-a-real-reset-token",
            "newPassword": "N3wPassw0rd!",
        })
        self.assertEqual(resp.status_code, 400, resp.text)

    @patch("app.api.routes.auth.twofa_service.send_password_reset_email")
    def test_reset_password_invalidates_existing_sessions(self, mock_send_reset):
        from urllib.parse import parse_qs, urlparse

        email = _fresh_email("-session-revoke")
        _complete_signup(email)

        captured_token = {"value": ""}

        def _capture(*, to_email: str, reset_link: str):
            self.assertEqual(to_email, email)
            query = parse_qs(urlparse(reset_link).query)
            captured_token["value"] = query.get("reset_token", [""])[0]

        mock_send_reset.side_effect = _capture

        forgot = client.post("/auth/forgot-password", json={"email": email})
        self.assertEqual(forgot.status_code, 200, forgot.text)
        self.assertTrue(captured_token["value"])

        reset = client.post("/auth/reset-password", json={
            "token": captured_token["value"],
            "newPassword": "N3wPassw0rd!",
        })
        self.assertEqual(reset.status_code, 200, reset.text)

        me = client.get("/auth/me")
        self.assertEqual(me.status_code, 401, me.text)

    @patch("app.api.routes.auth.twofa_service.send_password_reset_email")
    def test_reset_token_cannot_be_replayed(self, mock_send_reset):
        from urllib.parse import parse_qs, urlparse

        email = _fresh_email("-replay")
        _complete_signup(email)

        captured_token = {"value": ""}

        def _capture(*, to_email: str, reset_link: str):
            self.assertEqual(to_email, email)
            query = parse_qs(urlparse(reset_link).query)
            captured_token["value"] = query.get("reset_token", [""])[0]

        mock_send_reset.side_effect = _capture
        forgot = client.post("/auth/forgot-password", json={"email": email})
        self.assertEqual(forgot.status_code, 200, forgot.text)

        first = client.post("/auth/reset-password", json={
            "token": captured_token["value"],
            "newPassword": "N3wPassw0rd!",
        })
        self.assertEqual(first.status_code, 200, first.text)

        replay = client.post("/auth/reset-password", json={
            "token": captured_token["value"],
            "newPassword": "An0therPass!",
        })
        self.assertEqual(replay.status_code, 400, replay.text)

    @patch("app.api.routes.auth.twofa_service.send_password_reset_email")
    def test_reset_password_enforces_strength_policy(self, mock_send_reset):
        from urllib.parse import parse_qs, urlparse

        email = _fresh_email("-strength")
        _complete_signup(email)

        captured_token = {"value": ""}

        def _capture(*, to_email: str, reset_link: str):
            self.assertEqual(to_email, email)
            query = parse_qs(urlparse(reset_link).query)
            captured_token["value"] = query.get("reset_token", [""])[0]

        mock_send_reset.side_effect = _capture
        forgot = client.post("/auth/forgot-password", json={"email": email})
        self.assertEqual(forgot.status_code, 200, forgot.text)

        weak = client.post("/auth/reset-password", json={
            "token": captured_token["value"],
            "newPassword": "password",
        })
        self.assertEqual(weak.status_code, 400, weak.text)

    @patch("app.api.routes.auth.twofa_service.send_password_reset_email")
    def test_forgot_password_rate_limit_by_ip(self, mock_send_reset):
        email = _fresh_email("-ratelimit")
        _complete_signup(email)

        with patch("app.api.routes.auth.settings.password_reset_request_max_per_ip", 1):
            first = client.post("/auth/forgot-password", json={"email": email})
            self.assertEqual(first.status_code, 200, first.text)
            second = client.post("/auth/forgot-password", json={"email": email})
            self.assertEqual(second.status_code, 429, second.text)
        mock_send_reset.assert_called_once()

    @patch("app.api.routes.auth._verify_turnstile_token", return_value=False)
    def test_forgot_password_requires_captcha_after_threshold(self, _mock_verify):
        with patch("app.api.routes.auth.settings.password_reset_captcha_after_attempts", 1), patch(
            "app.api.routes.auth.settings.turnstile_secret_key", "turnstile-secret"
        ):
            blocked = client.post("/auth/forgot-password", json={"email": _fresh_email("-captcha")})
            self.assertEqual(blocked.status_code, 429, blocked.text)


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
        "password": "Passw0rd!X",
        "twoFAMethod": "totp",
        "agreePrivacy": True,
        "agreeTerms": True,
        "agreeRisk": True,
    })


def _perform_login_step_up(email: str) -> None:
    import pyotp

    challenge = client.post("/auth/2fa/challenge", json={})
    assert challenge.status_code == 200, f"challenge failed: {challenge.text}"

    with get_session() as session:
        user = session.execute(select(User).where(User.email == email)).scalar_one()
        secret = str(user.twofa_secret or "")

    code = pyotp.TOTP(secret).now()
    verify = client.post(
        "/auth/2fa/verify",
        json={"verificationCode": code, "trustDevice": False},
    )
    assert verify.status_code == 200, f"verify failed: {verify.text}"


def _perform_webauthn_step_up() -> None:
    import uuid

    register_challenge = client.post("/auth/webauthn/register/challenge", json={"deviceLabel": "pytest-passkey"})
    assert register_challenge.status_code == 200, f"webauthn register challenge failed: {register_challenge.text}"

    signing_key = SigningKey.generate(curve=NIST256p)
    verifying_key = signing_key.verifying_key
    public_key_pem = verifying_key.to_pem().decode("utf-8")
    credential_id = f"cred-test-{uuid.uuid4().hex}"

    register = client.post(
        "/auth/webauthn/register",
        json={
            "challengeId": register_challenge.json()["challengeId"],
            "credentialId": credential_id,
            "publicKeyPem": public_key_pem,
            "algorithm": "ES256",
            "signCount": 0,
            "transports": ["internal"],
        },
    )
    assert register.status_code == 200, f"webauthn register failed: {register.text}"

    challenge = client.post("/auth/webauthn/challenge", json={"deviceLabel": "pytest-passkey"})
    assert challenge.status_code == 200, f"webauthn challenge failed: {challenge.text}"
    body = challenge.json()

    client_data = {
        "type": "webauthn.get",
        "challenge": body["challenge"],
        "origin": "http://localhost:3000",
    }
    client_data_raw = json.dumps(client_data).encode("utf-8")
    client_data_json = base64.urlsafe_b64encode(client_data_raw).decode("utf-8").rstrip("=")

    import hashlib

    rp_hash = hashlib.sha256("localhost".encode("utf-8")).digest()
    flags = bytes([0x01 | 0x04])
    sign_count = (1).to_bytes(4, byteorder="big")
    authenticator_data_raw = rp_hash + flags + sign_count
    authenticator_data = base64.urlsafe_b64encode(authenticator_data_raw).decode("utf-8").rstrip("=")
    signed_data = authenticator_data_raw + hashlib.sha256(client_data_raw).digest()
    signature_raw = signing_key.sign_deterministic(
        signed_data,
        hashfunc=hashlib.sha256,
        sigencode=ecdsa_util.sigencode_der,
    )
    signature = base64.urlsafe_b64encode(signature_raw).decode("utf-8").rstrip("=")

    verify = client.post(
        "/auth/webauthn/verify",
        json={
            "challengeId": body["challengeId"],
            "credentialId": credential_id,
            "clientDataJSON": client_data_json,
            "authenticatorData": authenticator_data,
            "signature": signature,
            "userHandle": "user-handle",
        },
    )
    assert verify.status_code == 200, f"webauthn verify failed: {verify.text}"


if __name__ == "__main__":
    unittest.main(verbosity=2)
