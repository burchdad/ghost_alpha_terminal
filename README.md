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
			forecast.py
			options.py
			signals.py
		services/
			kronos_service.py
			options_service.py
			signal_engine.py
			advanced.py
		models/
			schemas.py
		core/
			config.py
		utils/
			data_loader.py
		celery_app.py
		tasks.py
	requirements.txt

frontend/
	app/
		page.tsx
		dashboard/page.tsx
		globals.css
	components/
		Chart.tsx
		ForecastPanel.tsx
		OptionsPanel.tsx
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
- `POST /trade`
- `GET /performance/{symbol}`
- `POST /backtest`
- `GET /portfolio`
- `POST /execute`
- `GET /control`
- `POST /control/kill-switch`

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