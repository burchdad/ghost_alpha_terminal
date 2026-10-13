"""Offline email transport tests. Does not import app.main or contact providers."""
from __future__ import annotations

import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
from fastapi import HTTPException

from app.core.config import Settings
from app.services import notification_service, twofa_service


class TestResendEmail(unittest.TestCase):
    def setUp(self):
        self.settings = SimpleNamespace(
            resend_api_key="re_test_only", resend_from="Alpha <alpha@example.com>",
            smtp_host="", smtp_port=587, smtp_username="", smtp_password="",
            smtp_from_email="", smtp_use_starttls=True, smtp_use_ssl=False,
            otp_code_ttl_minutes=10, password_reset_ttl_minutes=30,
        )
        self.svc = twofa_service.TwoFAService()
        self.notifications = notification_service.NotificationService()
        self.settings_patch = patch.object(twofa_service, "settings", self.settings)
        self.settings_patch.start()
        self.addCleanup(self.settings_patch.stop)
        self.notif_patch = patch.object(notification_service, "settings", self.settings)
        self.notif_patch.start()
        self.addCleanup(self.notif_patch.stop)
        self.post_patch = patch.object(twofa_service.httpx, "post")
        self.post = self.post_patch.start()
        self.addCleanup(self.post_patch.stop)
        self.post.return_value = self.response(200, {"id": "test-email-id"})
        # Any accidentally unmocked network operation fails this test immediately.
        self.socket_patch = patch("socket.socket.connect", side_effect=AssertionError("Network disabled in email tests"))
        self.socket_patch.start()
        self.addCleanup(self.socket_patch.stop)

    def response(self, status, payload):
        return httpx.Response(status, json=payload, request=httpx.Request("POST", "https://api.resend.com/emails"))

    def send(self):
        self.svc._send_via_resend(to_email="recipient@example.com", subject="Subject", body="Body")

    def assert_payload(self, subject, body):
        self.post.assert_called_once_with(
            "https://api.resend.com/emails",
            headers={"Authorization": "Bearer re_test_only"},
            json={"from": "Alpha <alpha@example.com>", "to": ["recipient@example.com"], "subject": subject, "text": body},
            timeout=15.0, follow_redirects=False,
        )

    def test_plain_text_api_payload_and_timeout(self):
        self.send()
        self.assert_payload("Subject", "Body")

    def test_whitespace_trimmed_in_configuration(self):
        self.settings.resend_api_key = "  re_test_only  "
        self.settings.resend_from = "  Alpha <alpha@example.com>  "
        self.send()
        self.assert_payload("Subject", "Body")

    def test_smtp_sender_used_when_resend_sender_empty(self):
        self.settings.resend_from = ""
        self.settings.smtp_from_email = "fallback@example.com"
        self.send()
        self.assertEqual(self.post.call_args.kwargs["json"]["from"], "fallback@example.com")

    def test_missing_api_key_fails_before_send(self):
        for key in ("", "  ", "none", "NULL", None):
            with self.subTest(key=key):
                self.settings.resend_api_key = key
                with self.assertRaises(HTTPException) as caught:
                    self.send()
                self.assertEqual(caught.exception.status_code, 503)
        self.post.assert_not_called()

    def test_missing_sender_fails_before_send(self):
        for sender in ("", "  ", "none", "NULL", None):
            with self.subTest(sender=sender):
                self.settings.resend_from = sender
                with self.assertRaises(HTTPException) as caught:
                    self.send()
                self.assertEqual(caught.exception.status_code, 503)
        self.post.assert_not_called()

    def test_http_failures_and_redirects_are_sanitized(self):
        for status in (301, 400, 401, 403, 409, 422, 429, 500, 503):
            with self.subTest(status=status):
                self.post.return_value = self.response(status, {"message": "secret-token recipient@example.com Body"})
                with self.assertRaises(HTTPException) as caught:
                    self.send()
                self.assertEqual(caught.exception.status_code, 502)
                self.assertEqual(caught.exception.detail, f"Failed to send email via Resend (HTTP {status})")

    def test_transport_errors_are_sanitized_without_retry(self):
        self.post.side_effect = httpx.ConnectError("secret-token recipient@example.com Body")
        with self.assertRaises(HTTPException) as caught:
            self.send()
        self.assertEqual(caught.exception.status_code, 502)
        self.assertEqual(caught.exception.detail, "Failed to send email via Resend")
        self.post.assert_called_once()

    def test_timeout_is_sanitized_without_retry(self):
        self.post.side_effect = httpx.ReadTimeout("private message content")
        with self.assertRaises(HTTPException) as caught:
            self.send()
        self.assertEqual(caught.exception.detail, "Failed to send email via Resend")
        self.post.assert_called_once()

    def test_missing_or_invalid_message_id_is_not_success(self):
        for payload in ({}, {"id": ""}, {"id": " "}, {"id": None}, {"id": 12}, [], None):
            with self.subTest(payload=payload):
                self.post.return_value = self.response(200, payload)
                with self.assertRaises(HTTPException) as caught:
                    self.send()
                self.assertEqual(caught.exception.status_code, 502)

    def test_invalid_json_is_not_success(self):
        self.post.return_value = httpx.Response(200, text="not-json", request=httpx.Request("POST", "https://api.resend.com/emails"))
        with self.assertRaises(HTTPException) as caught:
            self.send()
        self.assertEqual(caught.exception.status_code, 502)

    def test_verification_template_is_unchanged(self):
        self.svc.send_email_code(to_email="recipient@example.com", code="123456")
        self.assert_payload("Your Ghost Alpha Terminal verification code", "Your verification code is 123456. This code expires in 10 minutes.")

    def test_password_reset_template_is_unchanged(self):
        self.svc.send_password_reset_email(to_email="recipient@example.com", reset_link="https://example.com/reset?token=test-only")
        self.assert_payload(
            "Reset your Ghost Alpha Terminal password",
            "We received a request to reset your password.\n\nReset link: https://example.com/reset?token=test-only\n\n"
            "This link expires in 30 minutes. If you did not request this, you can safely ignore this email.",
        )

    def test_security_alert_template_is_unchanged(self):
        self.svc.send_security_alert(to_email="recipient@example.com", method="email", ip_address="192.0.2.1", device="Test browser", location="Test location")
        self.assert_payload("Ghost Alpha Terminal security alert", "Event: New login detected\n2FA method: email\nIP address: 192.0.2.1\nDevice: Test browser\nLocation: Test location")

    def test_security_alert_defaults_are_unchanged(self):
        self.svc.send_security_alert(to_email="recipient@example.com", method="totp", ip_address=None, device=None, event="Password changed")
        self.assert_payload("Ghost Alpha Terminal security alert", "Event: Password changed\n2FA method: totp\nIP address: unknown\nDevice: unknown")

    def test_withdrawal_email_text_and_links_are_unchanged(self):
        # Renders email text only. No broker or withdrawal route is imported.
        self.svc.send_withdrawal_approval_email(to_email="recipient@example.com", amount=123.45, destination="test-destination", confirm_link="https://example.com/confirm?token=test-only", deny_link="https://example.com/deny?token=test-only", hold_minutes=15)
        self.assert_payload("Confirm or deny your withdrawal request", "A withdrawal request is currently held pending your approval.\n\nAmount: 123.45\nDestination: test-destination\nHold window: 15 minutes\n\nConfirm: https://example.com/confirm?token=test-only\nDeny: https://example.com/deny?token=test-only\n\nIf this was not you, deny immediately and rotate credentials.")

    def test_otp_prefers_resend_over_smtp(self):
        self.settings.smtp_host = "smtp.example.com"
        self.settings.smtp_from_email = "sender@example.com"
        with patch.object(self.svc, "_send_via_smtp") as smtp:
            self.svc.send_email_code(to_email="recipient@example.com", code="123456")
        self.post.assert_called_once()
        smtp.assert_not_called()

    def test_otp_provider_failure_falls_back_to_smtp(self):
        self.settings.smtp_host = "smtp.example.com"
        self.settings.smtp_from_email = "sender@example.com"
        self.post.return_value = self.response(401, {})
        with patch.object(self.svc, "_send_via_smtp") as smtp:
            self.svc.send_email_code(to_email="recipient@example.com", code="123456")
        smtp.assert_called_once_with(to_email="recipient@example.com", subject="Your Ghost Alpha Terminal verification code", body="Your verification code is 123456. This code expires in 10 minutes.")

    def test_otp_timeout_preserves_existing_smtp_fallback(self):
        self.settings.smtp_host = "smtp.example.com"
        self.settings.smtp_from_email = "sender@example.com"
        self.post.side_effect = httpx.ReadTimeout("test timeout")
        with patch.object(self.svc, "_send_via_smtp") as smtp:
            self.svc.send_email_code(to_email="recipient@example.com", code="123456")
        smtp.assert_called_once()
        self.post.assert_called_once()

    def test_otp_no_provider_remains_503(self):
        self.settings.resend_api_key = ""
        with self.assertRaises(HTTPException) as caught:
            self.svc.send_email_code(to_email="recipient@example.com", code="123456")
        self.assertEqual(caught.exception.status_code, 503)
        self.post.assert_not_called()

    def test_otp_both_provider_failures_remain_502(self):
        self.settings.smtp_host = "smtp.example.com"
        self.settings.smtp_from_email = "sender@example.com"
        self.post.return_value = self.response(503, {})
        with patch.object(self.svc, "_send_via_smtp", side_effect=HTTPException(502, "test SMTP failure")):
            with self.assertRaises(HTTPException) as caught:
                self.svc.send_email_code(to_email="recipient@example.com", code="123456")
        self.assertEqual(caught.exception.status_code, 502)
        self.assertIn("Resend failed:", caught.exception.detail)
        self.assertIn("SMTP fallback failed:", caught.exception.detail)

    def test_reset_failure_does_not_introduce_new_smtp_fallback(self):
        self.settings.smtp_host = "smtp.example.com"
        self.settings.smtp_from_email = "sender@example.com"
        self.post.return_value = self.response(503, {})
        with patch.object(self.svc, "_send_via_smtp") as smtp:
            with self.assertRaises(HTTPException):
                self.svc.send_password_reset_email(to_email="recipient@example.com", reset_link="https://example.com/reset")
        smtp.assert_not_called()

    def test_security_alert_failure_remains_nonblocking(self):
        self.post.return_value = self.response(503, {})
        self.svc.send_security_alert(to_email="recipient@example.com", method="totp", ip_address=None, device=None)
        self.post.assert_called_once()

    def test_security_alert_missing_provider_remains_nonblocking(self):
        self.settings.resend_api_key = ""
        self.svc.send_security_alert(to_email="recipient@example.com", method="totp", ip_address=None, device=None)
        self.post.assert_not_called()

    def test_smtp_starttls_and_auth_unchanged(self):
        self.settings.resend_api_key = ""
        self.settings.smtp_host = "smtp.example.com"
        self.settings.smtp_from_email = "sender@example.com"
        self.settings.smtp_username = "test-user"
        self.settings.smtp_password = "test-only"
        with patch.object(twofa_service.smtplib, "SMTP") as smtp:
            self.svc.send_email_code(to_email="recipient@example.com", code="123456")
        server = smtp.return_value.__enter__.return_value
        server.starttls.assert_called_once()
        server.login.assert_called_once_with("test-user", "test-only")
        server.send_message.assert_called_once()
        self.post.assert_not_called()

    def test_smtp_ssl_unchanged(self):
        self.settings.resend_api_key = ""
        self.settings.smtp_host = "smtp.example.com"
        self.settings.smtp_from_email = "sender@example.com"
        self.settings.smtp_use_ssl = True
        self.settings.smtp_port = 465
        with patch.object(twofa_service.smtplib, "SMTP_SSL") as smtp:
            self.svc.send_password_reset_email(to_email="recipient@example.com", reset_link="https://example.com/reset")
        smtp.return_value.__enter__.return_value.send_message.assert_called_once()
        self.assertEqual(smtp.call_args.args, ("smtp.example.com", 465))
        self.post.assert_not_called()

    def test_notification_routes_unchanged_body_to_resend(self):
        self.notifications._try_email("recipient@example.com", "Subject", "Body")
        self.assert_payload("Subject", "Body")

    def test_notification_failure_remains_nonblocking(self):
        self.post.return_value = self.response(503, {})
        self.notifications._try_email("recipient@example.com", "Subject", "Body")
        self.post.assert_called_once()

    def test_notification_smtp_path_remains_supported(self):
        self.settings.resend_api_key = ""
        self.settings.smtp_host = "smtp.example.com"
        with patch.object(twofa_service.twofa_service, "_send_via_smtp") as smtp:
            self.notifications._try_email("recipient@example.com", "Subject", "Body")
        smtp.assert_called_once_with(to_email="recipient@example.com", subject="Subject", body="Body")
        self.post.assert_not_called()


class TestEmailProviderStatus(unittest.TestCase):
    """Exercise the existing diagnostic function without initializing the app."""

    def status(self, **overrides):
        path = Path(__file__).parents[1] / "app/api/routes/auth.py"
        tree = ast.parse(path.read_text())
        functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                     and node.name in {"_is_configured_env", "provider_status"}]
        self.assertEqual(len(functions), 2)
        for node in functions:
            node.decorator_list = []
        namespace = {"settings": Settings.model_construct(**overrides)}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"), namespace)
        return namespace["provider_status"]()

    def test_resend_configuration_is_reported_without_secret(self):
        result = self.status(resend_api_key="re_test_only", resend_from="sender@example.com")
        self.assertTrue(result["email_resend"])
        self.assertEqual(result["resend_from"], "sender@example.com")
        self.assertNotIn("re_test_only", str(result))
        self.assertNotIn("email_sendgrid", result)

    def test_missing_configuration_remains_false(self):
        result = self.status()
        self.assertFalse(result["email_resend"])
        self.assertFalse(result["email_smtp"])

    def test_smtp_configuration_remains_reported(self):
        result = self.status(smtp_host="smtp.example.com", smtp_from_email="sender@example.com")
        self.assertFalse(result["email_resend"])
        self.assertTrue(result["email_smtp"])

    def test_api_key_without_sender_is_not_ready(self):
        result = self.status(resend_api_key="re_test_only")
        self.assertFalse(result["email_resend"])


if __name__ == "__main__":
    unittest.main()
