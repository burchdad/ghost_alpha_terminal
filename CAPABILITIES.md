# Ghost Alpha Terminal Capabilities

This document is a quick reference for what the platform can currently do.

## Platform Scope

- AI-assisted market forecasting and options-aware strategy signaling.
- Multi-agent swarm consensus with adaptive weighting.
- Risk filtering, position sizing, and execution guardrails.
- Portfolio and performance tracking with regime-aware analytics.
- Operator controls for kill switch and autonomous execution mode.
- Web dashboard for monitoring, controls, and simulation workflows.
- Target-seeking goal engine with trajectory-aware pressure control.
- Broad-universe opportunity scanner with allocation recommendations.

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

## Market Scanner Layer

- Universe includes global equities and crypto symbols.
- Pre-filter pipeline evaluates:
  - liquidity via average dollar volume
  - spread proxy
  - momentum
  - realized volatility
- Detailed ranking combines consensus confidence, expected value, and allocation quality.

## Safety and Risk Controls

- Guardrails reject low-quality or over-risk trades.
- Daily loss and drawdown limits enforced by control engine.
- Kill switch can hard-stop execution at runtime.

## Deployment Status

- Backend: Railway deployment validated.
- Frontend: Vercel deployment validated.
- Baseline checkpoint commit: `d63e810` on `main`.
