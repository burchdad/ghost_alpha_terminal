# Operator Runbook

This runbook is for on-call operation of Ghost Alpha in paper and live modes.

## A. Daily Startup Checks

- Open `/alpha` and verify broker connection banner status.
- Confirm execution mode is expected (`SIMULATION`, `PAPER_TRADING`, or `LIVE_TRADING`).
- Confirm kill switch and autonomous status are intentional.
- Check `/metrics/runtime-readiness` for scan freshness and 24h counters.

## B. Normal Operating Signals

- Scans refresh continuously with recent timestamps.
- Context/news calls return current data and audit entries.
- Execution history grows when actionable signals pass all gates.
- Decision audit trail entries are populated on each decision cycle.

## C. Incident Classes

### C1. API Timeout / 5xx Burst

- Set execution mode to `SIMULATION`.
- Disable autonomous mode.
- Verify `/health`, `/orchestrator/status`, and `/metrics/runtime-readiness`.
- Restart backend service if stuck and re-check scan freshness.

### C2. Broker Authentication Failure

- Check connection banner for auth state and last error.
- Reconnect broker OAuth from `/alpha`.
- Verify `/alpaca/oauth/status` and `/alpaca/account` return success.
- Keep execution in simulation until account checks are green.

### C3. Orders Rejected Repeatedly

- Inspect execution history error/reason fields.
- Distinguish guardrail rejections from broker-side rejections.
- Verify symbol tradability and sizing constraints.
- Reduce risk pressure or return to simulation while triaging.

### C4. Stale Market Intelligence

- Check `latest_scan_age_seconds` in `/metrics/runtime-readiness`.
- Trigger manual scan and verify candidate refresh.
- If still stale, pause autonomous mode and investigate data providers.

## D. Emergency Stop Procedure

1. Press kill switch in control panel.
2. Set execution mode to `SIMULATION`.
3. Disable autonomous mode.
4. Verify no new submitted executions in history feed.
5. Document incident time and trigger condition.

## E. Recovery Procedure

- Restore service health first (scan/context/news/account checks).
- Re-enable paper mode execution before live mode.
- Run one manual autonomous cycle.
- Verify decision and execution telemetry increments as expected.
- Resume normal mode only after stable behavior for 15+ minutes.

## F. Useful Endpoints

- `/health`
- `/orchestrator/status`
- `/orchestrator/scan/latest`
- `/agents/execution-history?limit=25`
- `/agents/audit/decisions?limit=25`
- `/metrics/lightweight?days=7`
- `/metrics/runtime-readiness`
- `/alpaca/oauth/status`
- `/alpaca/account`
