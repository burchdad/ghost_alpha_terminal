# Ghost Alpha Terminal Capabilities

This document is a quick reference for what the platform can currently do.

## Platform Scope

- AI-assisted market forecasting and options-aware strategy signaling.
- Multi-agent swarm consensus with adaptive weighting.
- Risk filtering, position sizing, and execution guardrails.
- Portfolio and performance tracking with regime-aware analytics.
- Operator controls for kill switch and autonomous execution mode.
- Launch operations telemetry for growth, funnel conversion, and runtime reliability.
- Web dashboard for monitoring, controls, and simulation workflows.
- Public features/trust surface for onboarding and conversion (`/features`).
- Target-seeking goal engine with trajectory-aware pressure control.
- Broad-universe opportunity scanner with allocation recommendations.
- Reality-check layer with success-probability and adjusted-goal guidance.

## Backend Capabilities

### Forecasting and Signals

- `GET /forecast/{symbol}`
  - Produces directional forecast, confidence, volatility regime, and path.
- `GET /signal/{symbol}`
  - Produces rule-based strategy recommendation.

### Options Intelligence

- `GET /options/{symbol}`
  - Returns options chain metrics including IV, OI, volume, and Greeks.

### Swarm Decision Engine

- `GET /swarm/{symbol}`
  - Runs specialized agents (momentum, mean reversion, volatility, options).
  - Produces weighted consensus, confidence, and recommended trade framing.
  - Incorporates regime context and agent calibration data.

### Trade, Execution, and Control

- `POST /trade`
  - Records trade outcomes for learning and performance analytics.
- `POST /execute`
  - Execution path gated by safety checks and control status.
  - Regime and realized volatility are system-derived from recent candles.
  - Allocation sizing is goal-pressure aware when a target is active.
- `GET /agents/execution-mode` + `POST /agents/execution-mode`
  - Explicit execution mode selection:
    - `SIMULATION` for insight-only workflows
    - `PAPER_TRADING`
    - `LIVE_TRADING`
- `GET /agents/brokers/capabilities`
  - Returns broker capability matrix used by the execution router.
- `GET /control`
  - Returns current system status and risk gate state.
- `POST /control/kill-switch`
  - Enables or disables trade execution globally.
- `GET /control/autonomous`
  - Reads autonomous mode status.
- `POST /control/autonomous`
  - Toggles autonomous mode.
- `POST /control/autonomous/run-once`
  - Triggers a one-shot autonomous cycle.

### Portfolio and Performance

- `GET /portfolio`
  - Returns account posture, exposure, and allocation-level information.
- `GET /performance/{symbol}`
  - Returns PnL and win-rate analytics, including regime breakdowns.

### Backtesting and Simulation

- `POST /backtest`
  - Runs historical simulation with stop-loss, take-profit, and time exits.
  - Returns trade stats, drawdown, Sharpe proxy, and equity curve.

### Agent and Broker Operations

- `GET|POST /agents/*`
  - Agent management, diagnostics, and scoring-related endpoints.
  - Goal APIs:
    - `POST /agents/goal`
    - `GET /agents/goal/status`
  - Opportunity APIs:
    - `GET /agents/opportunities?limit=10`
    - Returns top opportunities, risk-adjusted setup ranking, and capital split recommendations.
- `GET|POST /alpaca/*`
  - Broker account, assets, orders, and positions routes.

### Telemetry and Launch Operations

- `GET /metrics/runtime-readiness`
  - Runtime cutover status including broker connectivity and execution health.
- `GET /telemetry/ops-summary`
  - Unified launch pulse for growth, funnel conversion, and reliability KPIs.
- `GET /telemetry/landing-summary`
  - Landing page variant and CTA conversion summary.

## Frontend Capabilities

- Real-time dashboard at `/dashboard` with:
  - Forecast, options, signal, and swarm visualization panels.
  - Agent insights and weighting views.
  - Backtest and performance analytics panels.
  - Portfolio posture panel.
  - Control panel with kill switch and autonomous mode controls.
  - Execution history panel for operator observability.

## Data and Learning

- Persistence for forecast history, signals, agent predictions, and trade outcomes.
- Feedback loop improves agent weighting over time via stored outcomes.
- Regime-aware attribution for better evaluation under varying market conditions.
- Agent scoring is historical-data-first, with fallback-generated metrics only when there is not yet enough realized outcome history.

## Goal and Trajectory Layer

- Goal inputs: starting capital, target capital, timeframe.
- Derived metrics:
  - required total return
  - required daily return
  - remaining required return pace
  - expected trajectory vs actual capital gap
- Output:
  - bounded `goal_pressure_multiplier` injected into allocator.
  - risk-aware adaptation when behind or ahead of trajectory.
  - reality-check diagnostics:
    - success probability estimate
    - stress classification
    - suggested target and/or timeframe when goal is likely unrealistic

## Market Scanner Layer

- Universe includes global equities and crypto symbols.
- Pre-filter pipeline evaluates:
  - liquidity via average dollar volume
  - spread proxy
  - momentum
  - realized volatility
- Detailed ranking combines consensus confidence, expected value, and allocation quality.
- **Dynamic universe** resolves live tradeable symbols from up to three external providers (Finnhub, Financial Modeling Prep, Massive Finance API) when `DYNAMIC_UNIVERSE_ENABLED=true`, with a 400+ ticker static fallback.
- **Discord signal injection**: symbols extracted from Discord channel messages are injected as a fourth priority tier in each scan cycle, with configurable confidence boost and per-cycle cap.

## Broker Abstraction and Routing

- Broker abstraction interface supports plug-and-play adapters.
- Active adapters:
  - **Alpaca** — equity/crypto order submission via API key; OAuth 2.0 flow supported for multi-tenant account linking.
  - **Coinbase** — crypto execution via CDP API key mode.
  - **Tradier** — equity and options order routing; sandbox and live account modes; options strategies (buy/sell single-leg; spreads, straddles, iron condors via multi-leg endpoints).
  - **Schwab** — OAuth 2.0 authorization code + PKCE flow; token storage in DB; equity order submission.
- Execution router chooses broker by asset class and liquidity-aware route rules.
- Per-broker policy controls (enabled flag, max position size, allowed asset classes) enforced at route time.
- Operator dashboard (`/alpha`) shows per-broker connection status, capability matrix, and policy configuration.

## Swarm Expansion

- Added `goal_alignment_agent`:
  - adjusts directional pressure in line with target trajectory demands.
- Added `execution_risk_agent`:
  - applies execution-quality veto logic before order submission.

## Explainability Standard

- Core recommendation and execution payloads include explainability blocks with:
  - reasoning
  - confidence
  - risk level
  - expected value
  - safeguards
  - decision inputs

## News Intelligence Layer

- Public-source news intelligence enriches symbol scoring with:
  - sentiment score
  - news momentum score
  - event strength
  - event flags
- **Runtime source controls**: operator can enable/disable individual sources and adjust per-source weights at runtime via `POST /control/news-feeds` without a redeploy.
- Compliance guardrails:
  - source whitelist endpoint (`GET /agents/news/sources`)
  - explicit data classification tags (`PUBLIC`, `DERIVED`, `RESTRICTED`, `UNKNOWN`)
  - auditable signal trail (`GET /agents/news/audit`)
- Symbol-level news signal endpoint:
  - `GET /agents/news/{symbol}`

## Context Intelligence Layer

- Context aggregation endpoint: `GET /agents/context/{symbol}`
- Produces bounded modifiers for confidence, risk, and opportunity ranking.
- Enforces compliance-safe behavior when data classification is not trusted.

## Portfolio Risk Governor

- Portfolio-level override layer after allocation and before execution.
- Decisions:
  - `ALLOW`
  - `RESIZE`
  - `BLOCK`
- Protects against over-concentration, over-exposure, and excessive drawdown.

## Decision Audit Trail

- Persistent decision lineage with query endpoints:
  - `GET /agents/audit/decisions`
  - `GET /agents/audit/decisions/{audit_id}`
- Stores normalized snapshots of goal, context, allocation, governor, execution, and explainability.

## Discord Integration

### Inbound Signal Feed

- Discord interactions webhook receiver at `POST /discord/inbound/events`.
- Ed25519 signature verification (`DISCORD_PUBLIC_KEY`) — unsigned requests are rejected.
- Inbound messages are stored as `DiscordInboundEvent` rows and immediately parsed for trade signals.
- Symbol extraction with noise-word filter (~120 blocked abbreviations like "AT", "FOR", "ON").
- **Options signal parsing**: regex extracts `SYMBOL $strike expiry CALL/PUT` patterns from natural language (e.g., "AAPL $200 call 5/16").
- Channel filtering: restrict signal ingestion to specific channel IDs via `DISCORD_SIGNAL_CHANNELS`.

### Signal-to-Scanner Pipeline

- `DiscordSignalService` bridges inbound events to the opportunity scanner with a 30-second TTL cache.
- Extracted symbols are injected as a fourth priority tier in each scan cycle (after Coinbase hot assets).
- Injected symbols receive a configurable confidence score boost (`DISCORD_SIGNAL_CONFIDENCE_BOOST`, default ×1.15).
- Per-cycle injection cap enforced via `DISCORD_SIGNAL_MAX_INJECT` (default 20).
- Operator-pinned symbols (`DiscordSignalWatchlist` DB table) persist across restarts and always appear in the priority set.

### Signal Management Endpoints

- `GET /discord/signals/status` — full snapshot: active symbols, options signals, source counts, config summary.
- `GET /discord/signals/watchlist` — operator-pinned watchlist entries.
- `POST /discord/signals/watchlist/{symbol}` — pin a symbol (high-trust required).
- `DELETE /discord/signals/watchlist/{symbol}` — unpin a symbol (high-trust required).

### Alpha Dashboard Panel

- `DiscordSignalPanel` on the Alpha operator dashboard shows:
  - Live/disabled status indicator.
  - Active symbols color-coded: purple = options signals, teal = pinned + active, blue = pinned-only, grey = event-only.
  - Options signals detail (direction, strike, expiry).
  - Pinned watchlist with Unpin buttons.
  - Pin-new-symbol form with asset class selector and optional note field.

### Outbound Alerts

- `DISCORD_ALERTS_ENABLED=true` + `DISCORD_WEBHOOK_URL` enables outbound runtime alerts.
- Rate limiting, deduplication, and critical-alert fast-path are all configurable.

## System Mode and Governance

- Three execution modes: `SIMULATION`, `PAPER_TRADING`, `LIVE_TRADING`.
- Predictive prevention layer assesses risk and can downgrade mode before a trade cycle.
- Operator kill switch (`POST /control/kill-switch`) halts execution globally.
- Autonomous mode controlled separately from execution mode (can run paper-trade cycles autonomously).

- Guardrails reject low-quality or over-risk trades.
- Daily loss and drawdown limits enforced by control engine.
- Kill switch can hard-stop execution at runtime.
- CSRF protection is enforced for state-changing authenticated requests.
- API scope/rate controls are applied to protect sensitive routes.
- Security headers and CSP policies are applied for browser hardening.

## Deployment Status

- Backend: Railway deployment validated.
- Frontend: Vercel deployment validated.
- Baseline checkpoint commit: `d63e810` on `main`.
