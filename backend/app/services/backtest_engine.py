from __future__ import annotations

from datetime import timezone

import numpy as np
import pandas as pd

from app.models.schemas import (
    BacktestRequest,
    BacktestResponse,
    ControlledExperimentComparison,
    ControlledExperimentResponse,
    ControlledExperimentRun,
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
from app.services.live_experiment_promotion_service import live_experiment_promotion_service
from app.services.strategy_evolution_service import strategy_evolution_service


class BacktestEngine:
    @staticmethod
    def _stability_score(*, win_rate: float, max_drawdown: float, starting_capital: float, sharpe: float, returns: list[float]) -> float:
        drawdown_pct = max_drawdown / max(starting_capital, 1.0)
        drawdown_component = max(0.0, 1.0 - min(drawdown_pct / 0.20, 1.0))
        sharpe_bounded = max(-1.0, min(sharpe, 2.0))
        sharpe_component = (sharpe_bounded + 1.0) / 3.0
        if len(returns) > 1:
            consistency_component = max(0.0, 1.0 - min(float(np.std(returns)) / 0.06, 1.0))
        else:
            consistency_component = 0.5
        score = (
            max(0.0, min(win_rate, 1.0)) * 0.40
            + drawdown_component * 0.30
            + sharpe_component * 0.20
            + consistency_component * 0.10
        )
        return round(max(0.0, min(score, 1.0)), 4)

    @staticmethod
    def _strategy_quality_from_history(history: dict[str, dict[str, float]]) -> dict[str, dict]:
        strategy_quality: dict[str, dict] = {}
        for strategy, stats in history.items():
            trades = int(stats.get("trades", 0))
            wins = int(stats.get("wins", 0))
            avg_pnl = float(stats.get("pnl", 0.0)) / max(trades, 1)
            if trades <= 0:
                continue
            win_rate = wins / max(trades, 1)
            quality_score = max(
                0.0,
                min(
                    1.0,
                    0.5
                    + (win_rate - 0.5) * 0.70
                    + (avg_pnl / max(abs(avg_pnl) + 200.0, 200.0)) * 0.15,
                ),
            )
            strategy_quality[strategy] = {
                "attempts": trades,
                "submitted": trades,
                "settled": trades,
                "submission_rate": 1.0,
                "win_rate": win_rate,
                "avg_pnl": avg_pnl,
                "slippage_flag_rate": 0.0,
                "quality_score": quality_score,
            }
        return strategy_quality

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
        strategy_trade_history: dict[str, dict[str, float]] = {}
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
            strategy_name = str(swarm.consensus.top_strategy or "UNKNOWN").upper()

            evolution_multiplier = 1.0
            if request.enable_evolution and len(trade_history) >= 5:
                strategy_quality = self._strategy_quality_from_history(strategy_trade_history)
                evolution = strategy_evolution_service.plan(strategy_quality=strategy_quality)
                reinforcement = evolution.get("reinforcement_weights", {})
                evolution_multiplier = float(reinforcement.get(strategy_name, 1.0) or 1.0)
                mutation = next(
                    (item for item in evolution.get("mutations", []) if str(item.get("strategy", "")).upper() == strategy_name),
                    None,
                )
                if mutation and str(mutation.get("action", "")).lower() in {"deprioritize", "mutate"} and swarm.consensus.confidence < 0.62:
                    equity_curve.append(
                        EquityPoint(
                            timestamp=current["timestamp"].to_pydatetime().replace(tzinfo=timezone.utc),
                            equity=round(balance, 4),
                        )
                    )
                    i += 1
                    continue

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
            sizing_balance = balance if request.enable_compounding else request.initial_capital
            sizing = position_sizer.calculate_position_size(
                account_balance=sizing_balance,
                risk_per_trade=request.risk_per_trade,
                stop_loss_pct=request.stop_loss_pct,
                entry_price=entry_price,
            )
            raw_units = (sizing_balance * request.risk_per_trade) / max(entry_price * request.stop_loss_pct, 1e-9)
            units = max(0.01, raw_units * max(0.60, min(evolution_multiplier, 1.35)))
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
            stats = strategy_trade_history.setdefault(strategy_name, {"trades": 0.0, "wins": 0.0, "pnl": 0.0})
            stats["trades"] += 1
            if outcome == "WIN":
                stats["wins"] += 1
            stats["pnl"] += pnl
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
        stability_score = self._stability_score(
            win_rate=win_rate,
            max_drawdown=max_drawdown,
            starting_capital=request.initial_capital,
            sharpe=sharpe,
            returns=trade_returns,
        )

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
            stability_score=stability_score,
            equity_curve=equity_curve,
            trade_history=trade_history,
        )

    def run_controlled_experiments(self, request: BacktestRequest) -> ControlledExperimentResponse:
        scenarios = [
            ("evolution_on_compounding_on", True, True),
            ("evolution_off_compounding_on", False, True),
            ("evolution_on_compounding_off", True, False),
            ("evolution_off_compounding_off", False, False),
        ]

        scenario_results: dict[str, BacktestResponse] = {}
        runs: list[ControlledExperimentRun] = []
        for label, enable_evolution, enable_compounding in scenarios:
            scenario_request = request.model_copy(
                update={
                    "enable_evolution": enable_evolution,
                    "enable_compounding": enable_compounding,
                }
            )
            result = self.run_backtest(scenario_request)
            scenario_results[label] = result
            runs.append(
                ControlledExperimentRun(
                    label=label,
                    enable_evolution=enable_evolution,
                    enable_compounding=enable_compounding,
                    total_trades=result.total_trades,
                    win_rate=result.win_rate,
                    total_pnl=result.total_pnl,
                    max_drawdown=result.max_drawdown,
                    sharpe_ratio=result.sharpe_ratio,
                    stability_score=result.stability_score,
                    ending_balance=result.ending_balance,
                )
            )

        comparisons: list[ControlledExperimentComparison] = []

        def add_pairwise(metric: str, mode_a: str, mode_b: str) -> None:
            a = scenario_results[mode_a]
            b = scenario_results[mode_b]
            a_value = float(getattr(a, metric))
            b_value = float(getattr(b, metric))
            comparisons.append(
                ControlledExperimentComparison(
                    metric=metric,  # type: ignore[arg-type]
                    mode_a_label=mode_a,
                    mode_b_label=mode_b,
                    mode_a_value=round(a_value, 6),
                    mode_b_value=round(b_value, 6),
                    delta_b_minus_a=round(b_value - a_value, 6),
                )
            )

        for metric_name in ("win_rate", "total_pnl", "max_drawdown", "stability_score"):
            add_pairwise(metric_name, "evolution_off_compounding_on", "evolution_on_compounding_on")
            add_pairwise(metric_name, "evolution_on_compounding_off", "evolution_on_compounding_on")

        live_status = live_experiment_promotion_service.status()
        control_mode = str(live_status.get("variant", "evolution_on_compounding_on"))
        control = scenario_results.get(control_mode) or scenario_results["evolution_on_compounding_on"]
        best = sorted(
            runs,
            key=lambda run: (run.stability_score, run.total_pnl, run.win_rate),
            reverse=True,
        )[0]

        control_drawdown = max(float(control.max_drawdown), 1e-6)
        outperforms_control = (
            best.total_trades >= 10
            and best.stability_score >= float(control.stability_score) + 0.015
            and best.total_pnl >= float(control.total_pnl) * 1.03
            and float(best.max_drawdown) <= control_drawdown * 1.02
        )
        promotion_applied = False
        promotion_reason = "Control retained."
        updated_live_status = live_status
        if outperforms_control and best.label != control_mode:
            promoted = live_experiment_promotion_service.promote(
                variant=best.label,
                source=f"controlled_experiment:{request.symbol.upper()}",
            )
            promotion_applied = bool(promoted.get("changed", False))
            updated_live_status = promoted
            promotion_reason = (
                "Winner outperformed live control: improved stability and PnL "
                "within drawdown tolerance, promoted to live mode."
            )

        return ControlledExperimentResponse(
            symbol=request.symbol.upper(),
            timeframe=request.timeframe,
            start_date=request.start_date,
            end_date=request.end_date,
            runs=runs,
            comparisons=comparisons,
            recommended_mode=best.label,
            control_mode=control_mode,
            promotion_applied=promotion_applied,
            promotion_reason=promotion_reason,
            live_mode=updated_live_status,
        )


backtest_engine = BacktestEngine()
