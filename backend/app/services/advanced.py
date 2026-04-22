"""
Advanced analytics services.
- Monte Carlo simulation for portfolio/symbol path forecasting
- Strategy optimizer scaffold
- Backtesting scaffold
- Portfolio manager scaffold
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np


def run_monte_carlo(
    *,
    symbol: str,
    starting_capital: float = 10_000.0,
    horizon_days: int = 30,
    n_simulations: int = 1_000,
    daily_returns: list[float] | None = None,
) -> dict[str, Any]:
    """
    Run a Monte Carlo simulation using either supplied daily_returns or
    a synthetic return distribution derived from the symbol name (fallback).

    Returns percentile paths, terminal distribution stats, and VaR estimates.
    """
    rng = np.random.default_rng(seed=42)

    # --- derive return distribution ---
    if daily_returns and len(daily_returns) >= 5:
        arr = np.array(daily_returns, dtype=float)
        mu = float(np.mean(arr))
        sigma = float(np.std(arr))
    else:
        # Synthetic fallback: conservative equity-like parameters
        mu = 0.0004
        sigma = 0.018

    sigma = max(sigma, 0.001)
    horizon_days = max(1, min(horizon_days, 252))
    n_simulations = max(100, min(n_simulations, 5_000))

    # --- simulate paths ---
    daily_shocks = rng.normal(loc=mu, scale=sigma, size=(n_simulations, horizon_days))
    # Compound: capital * prod(1 + r_i)
    path_multipliers = np.cumprod(1.0 + daily_shocks, axis=1)
    paths = starting_capital * path_multipliers  # shape (n_sims, horizon_days)

    terminal = paths[:, -1]
    pnl = terminal - starting_capital

    # Percentile paths (store every-other day to reduce payload size)
    step = max(1, horizon_days // 30)
    sample_days = list(range(0, horizon_days, step))
    if (horizon_days - 1) not in sample_days:
        sample_days.append(horizon_days - 1)

    p5_path = [round(float(np.percentile(paths[:, d], 5)), 2) for d in sample_days]
    p25_path = [round(float(np.percentile(paths[:, d], 25)), 2) for d in sample_days]
    p50_path = [round(float(np.percentile(paths[:, d], 50)), 2) for d in sample_days]
    p75_path = [round(float(np.percentile(paths[:, d], 75)), 2) for d in sample_days]
    p95_path = [round(float(np.percentile(paths[:, d], 95)), 2) for d in sample_days]

    # VaR / CVaR at 95% confidence (1-day, using return distribution)
    one_day_returns = daily_shocks[:, 0]
    var_95 = round(float(np.percentile(one_day_returns, 5)) * starting_capital, 2)
    cvar_95 = round(float(one_day_returns[one_day_returns <= np.percentile(one_day_returns, 5)].mean()) * starting_capital, 2)

    prob_profit = round(float(np.mean(terminal > starting_capital)), 4)
    prob_loss_10pct = round(float(np.mean(terminal < starting_capital * 0.90)), 4)

    return {
        "symbol": symbol,
        "starting_capital": starting_capital,
        "horizon_days": horizon_days,
        "n_simulations": n_simulations,
        "mu_daily": round(mu, 6),
        "sigma_daily": round(sigma, 6),
        "terminal": {
            "mean": round(float(np.mean(terminal)), 2),
            "median": round(float(np.median(terminal)), 2),
            "p5": round(float(np.percentile(terminal, 5)), 2),
            "p25": round(float(np.percentile(terminal, 25)), 2),
            "p75": round(float(np.percentile(terminal, 75)), 2),
            "p95": round(float(np.percentile(terminal, 95)), 2),
        },
        "pnl": {
            "mean": round(float(np.mean(pnl)), 2),
            "p5": round(float(np.percentile(pnl, 5)), 2),
            "p95": round(float(np.percentile(pnl, 95)), 2),
        },
        "risk": {
            "var_95_1day": var_95,
            "cvar_95_1day": cvar_95,
            "prob_profit": prob_profit,
            "prob_loss_10pct": prob_loss_10pct,
        },
        "paths": {
            "days": [d + 1 for d in sample_days],
            "p5": p5_path,
            "p25": p25_path,
            "p50": p50_path,
            "p75": p75_path,
            "p95": p95_path,
        },
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
    }


# Legacy stub names retained for backward compatibility
def run_monte_carlo_stub() -> dict:
    return run_monte_carlo(symbol="PORTFOLIO", starting_capital=10_000.0, horizon_days=30, n_simulations=500)


def run_strategy_optimizer_stub() -> dict:
    return {"status": "stub", "module": "strategy_optimizer", "message": "Strategy optimizer scaffold ready."}


def run_backtesting_stub() -> dict:
    return {"status": "stub", "module": "backtesting", "message": "Backtesting scaffold ready."}


def run_portfolio_manager_stub() -> dict:
    return {"status": "stub", "module": "portfolio_manager", "message": "Portfolio manager scaffold ready."}
