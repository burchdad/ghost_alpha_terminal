# Transactional email migration to Resend

Review-only patch prepared against `7a77201e05fd8db5430a934a0bcdcc836969c6ad`.
No deployment, live email, account change, credential change, or financial action
was performed while preparing this patch.

## Change

- Replace the SendGrid API transport with Resend's HTTPS email API using the
  already-pinned `httpx==0.28.1` dependency. Remove the SendGrid SDK dependency.
- Configure `RESEND_API_KEY` and `RESEND_FROM` instead of `SENDGRID_API_KEY` and
  `SENDGRID_FROM`. Old variable names are not aliases in this patch.
- Keep verification/2FA, reset, security, withdrawal-approval and operator-email
  subjects and plain-text bodies unchanged. Auth and trading logic is untouched.
  Update `/auth/provider-status` email diagnostics to `email_resend` and
  `resend_from` so they do not reference the removed settings.
- Keep existing SMTP support, including TLS settings, sender fallback and OTP
  fallback after an API failure. Reset/withdrawal messages retain their existing
  failure behavior; security alerts and operator notifications remain nonblocking.
- Reject provider errors, redirects, malformed JSON, and missing message IDs.
  Use a 15-second HTTPX timeout and no automatic HTTP retries. Provider response
  bodies and email contents are not included in Resend-facing error details.

## Gates before deploying

1. Recheck the deployed backend commit and review this patch on the current
   branch. This preparation verified GitHub main, not current runtime state.
2. Confirm the sending address on a Resend-verified domain. Preserve the existing
   sender identity where practical. Check required DNS authentication records
   and domain status; no DNS changes were made here.
3. Have the owner securely configure a suitable sending key as `RESEND_API_KEY`
   and the verified sender as `RESEND_FROM` in the backend secret manager. Do not
   paste credentials into code, chat, logs, or the example file. Credential setup
   requires its own authorization/secure handoff.
4. Inspect the current `SMTP_HOST` and sender configuration without exposing
   passwords. If SMTP still uses SendGrid, the fallback remains a SendGrid
   dependency. Do not remove it or claim complete independence until an approved
   replacement has been verified.
5. Confirm Resend quotas/rate limits are sufficient for OTP and operator traffic.
   Keep open/click tracking disabled for security-related transactional mail.
   Do not add link rewriting or hosted templates that alter approval/reset links.
6. Run the backend tests with the repository's pinned dependencies in an isolated
   environment. Do not connect tests to production databases, brokers, mail
   providers, or notification webhooks. The full app/auth suite was not run here.
7. Obtain deployment approval. Changing email transport does not authorize
   trading activity, withdrawal execution, security bypasses, or changes to
   auth/approval logic.
8. Perform an explicitly authorized, owner-controlled staging delivery check for
   the existing email paths. Verify provider acceptance AND inbox delivery,
   expiration behavior, exact links, fallback/failure handling, and audit records.
   For withdrawal-approval template checks, use synthetic data and a mock broker;
   never create or approve a real withdrawal to test email.

Deploying without the new variables can leave email unavailable unless the
existing SMTP configuration works. A Resend API message ID means acceptance,
not proof of delivery.

## Known behavior preserved

- An ambiguous API timeout followed by SMTP fallback can deliver duplicate OTP
  emails. The prior SendGrid flow had this behavior; this patch does not redesign
  retries, introduce idempotency, or change OTP semantics.
- Security alert and operator-email failures remain nonblocking. Their existing
  error visibility is limited; verify actual delivery before the cutover closes.
- SMTP credentials, TLS policy, and configuration validation are unchanged.
- No email-related tokens, links, TTLs, authentication checks, approval/deny
  handlers, or trading configuration are changed.

## Offline tests

From `backend/` with its dependencies installed:

```sh
APP_ENV=dev PYTHONPATH=. python -m unittest discover -s tests -p test_resend_email.py -v
```

The focused tests mock HTTP and SMTP, prohibit socket connections, and import
only email/config modules. The existing `test_twofa.py` email tests were updated
to mock HTTPX; all its non-email tests and helpers are unchanged.

Local review results: 32 new tests plus 5 updated email tests passed. The five
updated tests were loaded separately from their class to avoid initializing the
full application and its unrelated broker dependencies. This is not a full
backend or authentication integration pass. Runtime libraries available during
review were HTTPX 0.28.1, FastAPI 0.141.1, Pydantic 2.13.4 and Pydantic Settings
2.15.0; the last three differ from repository pins.

## Rollback and SendGrid retirement

Keep the previous release and its approved runtime configuration available for
rollback until staging and production delivery checks pass. Reverting the code
also reverts the SDK dependency and variable names. Do not cancel SendGrid on the
basis of this patch: other applications and any SendGrid-backed SMTP fallback
must be cleared separately.

## Official references

- [Resend send-email API](https://resend.com/docs/api-reference/emails/send-email)
- [Resend verified domains](https://resend.com/docs/dashboard/domains/introduction)
- [Resend API errors](https://resend.com/docs/api-reference/errors)
