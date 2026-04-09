# GHOST ALPHA TERMINAL

Production-oriented MVP for an AI-powered trading intelligence platform that combines:

- Kronos-style time-series forecasting service (mock-compatible)
- Options market intelligence (IV, OI, volume, Greeks)
- Rule-based strategy signal engine
- Multi-agent swarm consensus engine
- Persistent learning and feedback loop
- Risk management and position sizing engine
- Safety and execution control layer
- Real-time terminal-style dashboard UI

## Current Status

- Backend is deployed and verified on Railway.
- Frontend is deployed and verified on Vercel.
- Latest checkpoint commit on `main`: `d63e810`.
- Latest checkpoint commit on `main`: `48a1e98`.

For a concise feature inventory, see `CAPABILITIES.md`.

Operational launch docs:

- `GO_LIVE_CHECKLIST.md`
- `OPERATOR_RUNBOOK.md`

## Architecture

### Backend

- Python
- FastAPI + Uvicorn
- Pandas / NumPy
- Redis + Celery stubs for async/caching integration

### Frontend

- Next.js 14 (App Router)
- TypeScript
- TailwindCSS
- Recharts

### Data

- Mock market data for MVP bootstrapping
- PostgreSQL integration can be added next (Supabase/local)

## Repository Structure

```text
backend/
	app/
		main.py
		api/routes/
			agents.py
			alpaca.py
			backtest.py
			control.py
			execute.py
			forecast.py
			options.py
			performance.py
			portfolio.py
			signals.py
			swarm.py
			trade.py
		services/
			autonomous_runner.py
			capital_allocator.py
			execution_journal.py
			goal_engine.py
			kronos_service.py
			opportunity_scanner.py
			options_service.py
			portfolio_manager.py
			signal_engine.py
			swarm/
				swarm_manager.py
		models/
			schemas.py
		core/
			config.py
		db/
			models.py
			init_db.py
		celery_app.py
		tasks.py
	requirements.txt

frontend/
	app/
		page.tsx
		dashboard/page.tsx
		globals.css
	components/
		AgentPanel.tsx
		BacktestPanel.tsx
		Chart.tsx
		ControlPanel.tsx
		ExecutionHistoryPanel.tsx
		ForecastPanel.tsx
		OptionsPanel.tsx
		PerformancePanel.tsx
		PortfolioPanel.tsx
		SignalPanel.tsx
	package.json
```

## Quick Start

### 1. Start Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API endpoints:

- `GET /health`
- `GET /forecast/{symbol}?timeframe=1d`
- `GET /options/{symbol}`
- `GET /signal/{symbol}`
- `GET /swarm/{symbol}`
- `POST /backtest`
- `POST /trade`
- `POST /execute`
- `GET /portfolio`
- `GET /performance/{symbol}`
- `GET /control`
- `POST /control/kill-switch`
- `GET /control/autonomous`
- `POST /control/autonomous`
- `POST /control/autonomous/run-once`
- `GET /agents/*` (agent settings, scoring, and diagnostics)
- `POST /agents/goal` (set target capital + timeframe)
- `GET /agents/goal/status` (trajectory and pressure tracking)
- `GET /agents/opportunities?limit=10` (top opportunities + allocation split)
- `GET /agents/execution-mode` and `POST /agents/execution-mode` (insight-only/paper/live)
- `GET /agents/brokers/capabilities` (broker capability matrix used by router)
- `GET /agents/news/sources` (whitelisted public news sources)
- `GET /agents/news/{symbol}` (news/event signal for symbol)
- `GET /agents/news/audit?limit=50` (news signal audit log)
- `GET /agents/context/{symbol}` (context intelligence modifiers)
- `GET /agents/audit/decisions?limit=50` (decision audit summary list)
- `GET /agents/audit/decisions/{audit_id}` (full decision lineage payload)
- `GET|POST /alpaca/*` (broker connectivity and order/position operations)
- `GET /metrics/runtime-readiness` (cutover and operator telemetry snapshot)

Example trade outcome payload:

```json
{
	"symbol": "AAPL",
	"strategy": "BUY_CALL",
	"entry_price": 100.0,
	"exit_price": 104.5
}
```

### 2. Start Frontend

```bash
cd frontend
npm install
NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev
```

Open `http://localhost:3000` and go to `/dashboard`.

## Deployment Notes

- Frontend (Vercel): set `NEXT_PUBLIC_API_BASE` to your backend URL (for example, Railway service URL).
- Backend (Railway): ensure all required env values are configured in Railway project variables.
- CORS is controlled via backend settings in `backend/app/core/config.py`.

## Service Behavior

### Kronos Service

- Loads mock-compatible Kronos model pipeline
- Generates:
	- Direction (`UP`, `DOWN`, `SIDEWAYS`)
	- Confidence score
	- Volatility regime (`LOW`, `MEDIUM`, `HIGH`)
	- Forecasted price path

### Options Service

- Returns options chain with strikes and metrics:
	- Implied volatility
	- Open interest
	- Volume
- Computes Greeks (Delta, Gamma, Theta, Vega) with Black-Scholes style approximation

### Signal Engine

Rule-based decision logic:

- Bullish + low IV -> `BUY_CALL`
- Bullish + high IV -> `SELL_PUT_SPREAD`
- High volatility regime -> `STRADDLE`
- Range bound -> `IRON_CONDOR`
- Otherwise -> `HOLD`

### Swarm Layer

- Runs multiple specialized agents:
	- Momentum agent
	- Volatility agent
	- Mean-reversion agent
	- Options agent
- Scores each agent using mock live metrics:
	- Accuracy
	- Win rate
	- Confidence calibration
- Produces weighted consensus output:
	- Final bias
	- Consensus confidence
	- Top strategy / recommended trade

Frontend dashboard now includes an `AgentPanel` showing agent predictions, confidence, and leaderboard-style ranking.

Confidence calibration is applied in scoring:

- `calibration_factor = actual_accuracy / predicted_confidence`
- `adjusted_confidence = raw_confidence * calibration_factor`

Swarm agent breakdown now exposes both:

- `raw_confidence`
- `adjusted_confidence`

### Goal Engine + Trajectory Awareness

- Goal layer accepts target inputs (`start_capital`, `target_capital`, `timeframe_days`).
- System computes required return, remaining required pace, and trajectory gap.
- A bounded goal-pressure multiplier is produced and injected into allocation sizing.
- When trajectory falls behind, sizing pressure can increase within hard risk limits.
- Reality Check outputs include:
	- success probability estimate
	- stress level (`LOW`, `MEDIUM`, `HIGH`, `EXTREME`)
	- adjusted goal/timeframe suggestions for unrealistic targets

### Opportunity Scanner + Pre-Filter

- Broad ticker universe includes US/global equities plus crypto symbols.
- Pre-filter pipeline evaluates liquidity, spread proxy, momentum, and realized volatility.
- Scanner returns ranked opportunities with risk-adjusted allocation recommendations.
- API includes capital split suggestions for top tradable setups.

### Optional Execution Layer

- Swarm execution mode is explicitly selectable:
	- `SIMULATION` (insight-only/manual copy)
	- `PAPER_TRADING`
	- `LIVE_TRADING`
- Dashboard exposes this as a control-plane setting so execution is never forced.

### Broker Router + Adapter Layer

- Execution path now uses a broker abstraction with pluggable adapters.
- Current adapters:
	- `alpaca` (active)
	- `coinbase` (stubbed interface for next integration)
- Router selects execution venue by asset class and liquidity score.
- Capability map exposes support for equities/crypto/options/fractional/leverage.

### Swarm Role Expansion

- Added `goal_alignment_agent`:
	- adjusts directional aggression based on goal pressure and trajectory gap.
- Added `execution_risk_agent`:
	- vetoes trades under unstable fill conditions (volatility/volume anomalies).

### Explainability Layer

- Recommendation and execution responses now include structured explainability:
	- reasoning summary
	- confidence
	- risk level
	- expected value
	- safeguards applied
	- decision inputs used

### News Intelligence Layer

- Added public-source news intelligence service with source whitelisting.
- Each symbol now has:
	- `sentiment_score`
	- `news_momentum_score`
	- `event_strength`
	- `event_flags`
- Data classification is explicitly tagged (`PUBLIC`/`DERIVED`/`RESTRICTED`/`UNKNOWN`).
- Signals are auditable with timestamp, source list, and classification.
- Opportunity ranking includes a bounded news alpha boost.

### Context Intelligence Layer

- Context layer merges public news signals into bounded modifiers:
	- `confidence_modifier`
	- `risk_modifier`
	- `opportunity_boost`
- Compliance guardrail: `RESTRICTED`/`UNKNOWN` classifications cannot increase risk or confidence.

### Portfolio Risk Governor

- Final gate before execution to enforce portfolio-level controls:
	- per-trade notional caps
	- total exposure caps
	- sector concentration caps
	- drawdown hard stop
- Governor can `ALLOW`, `RESIZE`, or `BLOCK` a decision with explicit rationale.

### Decision Audit Trail

- Every execute/swarm decision now persists a full audit envelope including:
	- goal snapshot
	- context snapshot
	- allocation + governor snapshots
	- execution snapshot
	- explainability snapshot
- Audit records are queryable by summary and by id for full traceability.

### Market Regime Detection

- `regime_detector.py` classifies market state as:
	- `TRENDING`
	- `RANGE_BOUND`
	- `HIGH_VOLATILITY`
- Inputs include recent price action, realized volatility, ATR proxy, and trend strength.
- Regime is injected into swarm agent execution so agents adapt behavior by market context.
- Swarm response includes:
	- `regime`
	- `regime_confidence`
- Dashboard header displays live regime and confidence.

### Performance by Regime

- `trade_outcomes` now stores the execution regime per trade (`TRENDING`, `RANGE_BOUND`, `HIGH_VOLATILITY`).
- `GET /performance/{symbol}` includes `by_regime` analytics with:
	- `win_rate`
	- `avg_pnl`
	- `total_trades`
- Frontend `PerformancePanel` shows a dedicated regime breakdown table for operator validation.

### Persistent Learning Layer

SQLAlchemy-backed persistence tracks model and trade feedback in these tables:

- `forecast_history`
- `signal_history`
- `agent_predictions`
- `trade_outcomes`

Behavior:

- Every `/swarm/{symbol}` call stores forecast, signal, and agent predictions.
- Every `POST /trade` stores realized outcome and PnL.
- Agent scoring pulls historical outcomes to adapt weighting over time.
- `GET /performance/{symbol}` returns agent leaderboard and strategy success rates.

### Backtesting & Simulation Layer

- Historical data service provides date-range OHLCV replay (mock for MVP).
- Backtest engine replays candles and runs:
	- Forecast generation
	- Swarm consensus
	- Signal engine
	- Trade simulation
- Simulation supports:
	- Fixed take-profit
	- Stop-loss
	- Time-based exit (`max_hold_periods`)
- `POST /backtest` returns:
	- Total trades
	- Win rate
	- Total PnL
	- Max drawdown
	- Sharpe ratio
	- Equity curve
	- Trade history

Example backtest payload:

```json
{
	"symbol": "AAPL",
	"timeframe": "1d",
	"start_date": "2025-01-01T00:00:00Z",
	"end_date": "2026-01-01T00:00:00Z",
	"take_profit_pct": 0.03,
	"stop_loss_pct": 0.02,
	"max_hold_periods": 5
}
```

Frontend dashboard now includes `BacktestPanel` for equity curve visualization, trade history, and key simulation stats.

### Risk & Position Sizing Layer

- Position sizing uses fixed-fractional risk model:
	- `position_size = (account_balance * risk_per_trade) / (entry_price * stop_loss_pct)`
- Risk engine evaluates trade quality via:
	- risk/reward ratio
	- max loss amount
	- probability-adjusted expected value
- Portfolio manager tracks:
	- active positions
	- total exposure
	- sector concentration
	- max concurrent trades

Integration behavior:

- `/swarm/{symbol}` now includes execution guidance:
	- `position_size`
	- `risk_level`
	- `expected_value`
- `/backtest` now applies dynamic position sizing and capital compounding.
- Dashboard includes `PortfolioPanel` for balance, exposure, and allocation view.

### Safety & Control Layer

- Trade guardrails reject executions when:
	- confidence < 60%
	- expected value <= 0
	- risk/reward < 1.5
	- position size / notional exceeds thresholds
- Control engine enforces global risk stops:
	- daily loss limit: 5% of starting account
	- max rolling drawdown: 10%
- Kill switch gate blocks all `/execute` calls when disabled.
- Rejected trades are logged with timestamp, symbol, and reason.

Frontend dashboard now includes `ControlPanel` with:

- System status (`ACTIVE` / `PAUSED`)
- Safe mode and current drawdown/loss telemetry
- Kill switch toggle
- Recent rejection log

## Advanced Feature Stubs Included

`backend/app/services/advanced.py` includes placeholder modules for:

- Monte Carlo simulation
- Strategy optimizer
- Backtesting engine
- Portfolio manager

## Notes

- This MVP uses deterministic mock data for stable local development.
- Set `use_mock_data=false` and configure `kronos_model_id` in env when connecting a real model/API.