from __future__ import annotations

from datetime import timezone

import numpy as np
import pandas as pd

from app.models.schemas import (
    BacktestRequest,
    BacktestResponse,
    EquityPoint,
    ForecastResponse,
    SimulatedTrade,
)
from app.services.agent_manager import agent_manager
from app.services.consensus_engine import consensus_engine
from app.services.historical_data_service import historical_data_service
from app.services.options_service import options_service
from app.services.position_sizer import position_sizer
from app.services.regime_detector import regime_detector
from app.services.signal_engine import signal_engine
from app.services.simulation_engine import simulation_engine


class BacktestEngine:
    def _forecast_from_window(self, symbol: str, timeframe: str, window: pd.DataFrame, timestamp) -> ForecastResponse:
        closes = window["close"].to_numpy(dtype=float)
        returns = np.diff(closes) / closes[:-1] if len(closes) > 1 else np.array([0.0])

        mean_return = float(np.mean(returns)) if len(returns) else 0.0
        vol = float(np.std(returns) * np.sqrt(252)) if len(returns) else 0.0

        if mean_return > 0.001:
            direction = "UP"
        elif mean_return < -0.001:
            direction = "DOWN"
        else:
            direction = "SIDEWAYS"

        if vol < 0.15:
            volatility = "LOW"
        elif vol < 0.35:
            volatility = "MEDIUM"
        else:
            volatility = "HIGH"

        range_bound = abs(mean_return) < 0.0008 and vol < 0.22
        confidence = float(min(0.95, max(0.51, abs(mean_return) * 200 + 0.55)))

        last_price = float(closes[-1])
        horizon = 10
        rng = np.random.default_rng(abs(hash(f"{symbol}:{timestamp}")) % (2**32))
        noise = rng.normal(0, vol / np.sqrt(252), horizon)
        path = last_price * np.cumprod(1 + mean_return + noise)

        ts = timestamp.to_pydatetime().replace(tzinfo=timezone.utc)
        return ForecastResponse(
            symbol=symbol.upper(),
            timeframe=timeframe,
            direction=direction,
            confidence=round(confidence, 3),
            volatility=volatility,
            range_bound=range_bound,
            forecast_prices=[round(float(x), 2) for x in path],
            generated_at=ts,
        )

    def run_backtest(self, request: BacktestRequest) -> BacktestResponse:
        df = historical_data_service.load_historical_data(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
        )

        warmup = 25
        balance = request.initial_capital
        peak_equity = balance
        drawdowns: list[float] = []
        trade_returns: list[float] = []
        trade_history: list[SimulatedTrade] = []
        equity_curve: list[EquityPoint] = []

        i = warmup
        while i < len(df) - 2:
            window = df.iloc[i - warmup : i + 1]
            current = df.iloc[i]

            forecast = self._forecast_from_window(request.symbol, request.timeframe, window, current["timestamp"])

            options_data = options_service.get_options_chain(request.symbol)
            options_data.underlying_price = round(float(current["close"]), 2)

            realized_vol = float(np.std(np.diff(window["close"]) / window["close"].to_numpy()[:-1]) * np.sqrt(252))
            options_data.avg_iv = round(max(8.0, min(95.0, realized_vol * 100 * 1.1)), 2)
            regime = regime_detector.detect_from_dataframe(window)

            signal = signal_engine.generate_signal(request.symbol, forecast, options_data)
            agent_outputs = agent_manager.run_agents(
                request.symbol,
                forecast,
                options_data,
                regime=regime.regime,
            )
            swarm = consensus_engine.generate_consensus(request.symbol, agent_outputs)

            side = "LONG" if swarm.consensus.final_bias == "BULLISH" else "SHORT" if swarm.consensus.final_bias == "BEARISH" else "LONG"
            if signal.signal == "HOLD" and swarm.consensus.final_bias == "NEUTRAL":
                equity_curve.append(
                    EquityPoint(
                        timestamp=current["timestamp"].to_pydatetime().replace(tzinfo=timezone.utc),
                        equity=round(balance, 4),
                    )
                )
                i += 1
                continue

            entry_price = float(current["close"])
            sizing = position_sizer.calculate_position_size(
                account_balance=balance,
                risk_per_trade=request.risk_per_trade,
                stop_loss_pct=request.stop_loss_pct,
                entry_price=entry_price,
            )
            units = max(1.0, sizing["position_size"])
            forward = df.iloc[i + 1 : i + 1 + request.max_hold_periods]
            if forward.empty:
                break
            future_prices = [float(v) for v in forward["close"].tolist()]

            periods_held, exit_price, pnl = simulation_engine.resolve_trade(
                side=side,
                entry_price=entry_price,
                future_prices=future_prices,
                take_profit_pct=request.take_profit_pct,
                stop_loss_pct=request.stop_loss_pct,
            )
            pnl = pnl * units

            exit_idx = min(i + periods_held, len(df) - 1)
            exit_row = df.iloc[exit_idx]
            position_notional = max(entry_price * units, 1e-6)
            return_pct = pnl / position_notional
            outcome = "WIN" if pnl >= 0 else "LOSS"

            trade_history.append(
                SimulatedTrade(
                    entry_time=current["timestamp"].to_pydatetime().replace(tzinfo=timezone.utc),
                    exit_time=exit_row["timestamp"].to_pydatetime().replace(tzinfo=timezone.utc),
                    side=side,
                    strategy=swarm.consensus.top_strategy,
                    entry_price=round(entry_price, 4),
                    exit_price=round(exit_price, 4),
                    pnl=round(pnl, 4),
                    return_pct=round(return_pct, 4),
                    outcome=outcome,
                )
            )

            balance += pnl
            peak_equity = max(peak_equity, balance)
            drawdown = peak_equity - balance
            drawdowns.append(drawdown)
            trade_returns.append(return_pct)
            equity_curve.append(
                EquityPoint(
                    timestamp=exit_row["timestamp"].to_pydatetime().replace(tzinfo=timezone.utc),
                    equity=round(balance, 4),
                )
            )

            i = exit_idx + 1

        total_trades = len(trade_history)
        wins = sum(1 for t in trade_history if t.outcome == "WIN")
        win_rate = (wins / total_trades) if total_trades else 0.0
        total_pnl = round(sum(t.pnl for t in trade_history), 4)
        max_drawdown = round(max(drawdowns) if drawdowns else 0.0, 4)

        if len(trade_returns) > 1 and np.std(trade_returns) > 0:
            sharpe = float(np.mean(trade_returns) / np.std(trade_returns) * np.sqrt(len(trade_returns)))
        else:
            sharpe = 0.0

        return BacktestResponse(
            symbol=request.symbol.upper(),
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
            starting_capital=round(request.initial_capital, 2),
            ending_balance=round(balance, 2),
            total_trades=total_trades,
            win_rate=round(win_rate, 4),
            total_pnl=total_pnl,
            max_drawdown=max_drawdown,
            sharpe_ratio=round(sharpe, 4),
            equity_curve=equity_curve,
            trade_history=trade_history,
        )


backtest_engine = BacktestEngine()
