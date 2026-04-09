# Go-Live Switch Checklist

This checklist is for the exact cutover from paper runtime to live-capital runtime after broker/account approval.

## 1. Approval and Access

- Confirm Alpaca app approval email and account trading approval are both complete.
- Confirm account permissions include live trading and required asset classes.
- Confirm OAuth app redirect URI and client credentials match production values.

## 2. Environment Readiness

- Confirm backend environment variables are set for production.
- Confirm frontend `NEXT_PUBLIC_API_BASE` points to production backend proxy.
- Confirm Alpaca credentials and OAuth credentials are present and non-empty.
- Confirm `ALPACA_PAPER=false` only when final live cutover starts.
- Keep `use_mock_data=false` in backend config for production runtime.

## 3. Safety Guardrails (Must Verify)

- Kill switch defaults to enabled only when operator is present.
- Daily loss limit, drawdown limit, and position sizing limits are confirmed.
- Max concurrent positions is explicitly set and documented.
- Emergency stop procedure tested in paper mode within 24h before cutover.

## 4. Runtime Readiness (Pre-Cutover)

- `GET /metrics/runtime-readiness` returns healthy fields.
- `latest_scan_age_seconds` is low and scans are updating continuously.
- `news_audits_24h` and context signals are non-zero and current.
- Autonomous cycles run without endpoint failures.
- Decision audit and execution history streams respond with valid payloads.

## 5. Cutover Sequence

1. Disable autonomous mode.
2. Set execution mode to `SIMULATION`.
3. Toggle backend `ALPACA_PAPER=false` and redeploy.
4. Reconnect broker OAuth and verify status banner in `/alpha`.
5. Set execution mode to `LIVE_TRADING`.
6. Enable autonomous mode with minimum risk profile.
7. Observe first execution cycle manually.

## 6. First-Hour Monitoring

- Watch `/metrics/runtime-readiness` every 5 minutes.
- Verify submitted execution count increments as expected.
- Verify rejected executions are explainable (risk gates vs broker errors).
- Verify open positions and account equity match broker dashboard.
- Keep kill switch one click away during the entire first hour.

## 7. Rollback Conditions

Immediately revert to paper mode or engage kill switch if any of the following occur:

- Unexpected order volume or duplicate submissions.
- Repeated unexplained broker errors.
- Stale scans (`latest_scan_age_seconds` continually rising).
- Missing decision or execution audit trail while orders continue.
- Risk limits breached or drawdown behavior diverges from expected controls.
