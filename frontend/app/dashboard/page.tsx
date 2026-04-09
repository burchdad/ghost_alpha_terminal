"use client";

import { useEffect, useMemo, useState } from "react";

import Chart from "../../components/Chart";
import ControlPanel from "../../components/ControlPanel";
import ForecastPanel from "../../components/ForecastPanel";
import AgentPanel from "../../components/AgentPanel";
import BacktestPanel from "../../components/BacktestPanel";
import OptionsPanel from "../../components/OptionsPanel";
import PerformancePanel from "../../components/PerformancePanel";
import PortfolioPanel from "../../components/PortfolioPanel";
import SignalPanel from "../../components/SignalPanel";
import SwarmVisualizationPanel from "../../components/swarm/SwarmVisualizationPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type ForecastResponse = {
  symbol: string;
  direction: "UP" | "DOWN" | "SIDEWAYS";
  confidence: number;
  volatility: "LOW" | "MEDIUM" | "HIGH";
  range_bound: boolean;
  forecast_prices: number[];
};

type OptionContract = {
  strike: number;
  option_type: "CALL" | "PUT";
  iv: number;
  open_interest: number;
  volume: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
};

type OptionsResponse = {
  symbol: string;
  underlying_price: number;
  avg_iv: number;
  contracts: OptionContract[];
};

type SignalResponse = {
  signal: string;
  confidence: number;
  reasoning: string;
};

type AgentPerformance = {
  accuracy: number;
  win_rate: number;
  avg_return: number;
  confidence_calibration: number;
  composite_score: number;
};

type AgentDecision = {
  agent_name: string;
  bias: "BULLISH" | "BEARISH" | "NEUTRAL";
  confidence: number;
  raw_confidence: number | null;
  adjusted_confidence: number | null;
  suggested_strategy: string;
  reasoning: string;
  performance: AgentPerformance | null;
  weighted_confidence: number | null;
};

type SwarmResponse = {
  symbol: string;
  regime: "TRENDING" | "RANGE_BOUND" | "HIGH_VOLATILITY";
  regime_confidence: number;
  consensus: {
    final_bias: "BULLISH" | "BEARISH" | "NEUTRAL";
    confidence: number;
    top_strategy: string;
  };
  recommended_trade: string;
  position_size: number;
  risk_level: "LOW" | "MEDIUM" | "HIGH";
  expected_value: number;
  agent_breakdown: AgentDecision[];
};

type PerformanceAgentRow = {
  agent_name: string;
  accuracy: number;
  win_rate: number;
  avg_return: number;
  confidence_calibration: number;
  composite_score: number;
};

type PerformanceStrategyRow = {
  strategy: string;
  trades: number;
  win_rate: number;
  avg_pnl: number;
};

type PerformanceResponse = {
  symbol: string;
  best_agent: string;
  agent_leaderboard: PerformanceAgentRow[];
  top_strategies: PerformanceStrategyRow[];
  by_regime: Record<string, { win_rate: number; avg_pnl: number; total_trades: number }>;
};

type BacktestEquityPoint = {
  timestamp: string;
  equity: number;
};

type BacktestTrade = {
  entry_time: string;
  exit_time: string;
  side: "LONG" | "SHORT";
  strategy: string;
  entry_price: number;
  exit_price: number;
  pnl: number;
  return_pct: number;
  outcome: "WIN" | "LOSS";
};

type BacktestResponse = {
  symbol: string;
  timeframe: string;
  start_date: string;
  end_date: string;
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  max_drawdown: number;
  sharpe_ratio: number;
  equity_curve: BacktestEquityPoint[];
  trade_history: BacktestTrade[];
};

type PortfolioActivePosition = {
  symbol: string;
  strategy: string;
  side: string;
  entry_price: number;
  units: number;
  notional: number;
  sector: string;
  opened_at: string;
};

type PortfolioResponse = {
  account_balance: number;
  active_positions: PortfolioActivePosition[];
  total_exposure: number;
  risk_exposure_pct: number;
  sector_concentration: Record<string, number>;
  max_concurrent_trades: number;
};

type RejectedTradeLog = {
  timestamp: string;
  symbol: string;
  reason: string;
};

type ControlResponse = {
  trading_enabled: boolean;
  system_status: "ACTIVE" | "PAUSED";
  mode: "SAFE" | "NORMAL";
  daily_pnl: number;
  daily_loss: number;
  daily_loss_limit: number;
  rolling_drawdown: number;
  rolling_drawdown_pct: number;
  max_drawdown_limit_pct: number;
  rejected_trades: RejectedTradeLog[];
};

async function parseJsonOrNull<T>(res: Response): Promise<T | null> {
  if (!res.ok) {
    return null;
  }
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export default function DashboardPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [options, setOptions] = useState<OptionsResponse | null>(null);
  const [signal, setSignal] = useState<SignalResponse | null>(null);
  const [swarm, setSwarm] = useState<SwarmResponse | null>(null);
  const [performance, setPerformance] = useState<PerformanceResponse | null>(null);
  const [backtest, setBacktest] = useState<BacktestResponse | null>(null);
  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [control, setControl] = useState<ControlResponse | null>(null);

  const watchlist = useMemo(() => ["AAPL", "TSLA", "NVDA", "SPY", "MSFT", "AMD"], []);

  useEffect(() => {
    async function fetchAll() {
      const end = new Date();
      const start = new Date();
      start.setDate(end.getDate() - 240);

      const [fRes, oRes, sRes, swarmRes, perfRes, backtestRes, portfolioRes, controlRes] = await Promise.all([
        fetch(`${API_BASE}/forecast/${symbol}`),
        fetch(`${API_BASE}/options/${symbol}`),
        fetch(`${API_BASE}/signal/${symbol}`),
        fetch(`${API_BASE}/swarm/${symbol}`),
        fetch(`${API_BASE}/performance/${symbol}`),
        fetch(`${API_BASE}/backtest`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symbol,
            timeframe: "1d",
            start_date: start.toISOString(),
            end_date: end.toISOString(),
            take_profit_pct: 0.03,
            stop_loss_pct: 0.02,
            max_hold_periods: 5,
          }),
        }),
        fetch(`${API_BASE}/portfolio`),
        fetch(`${API_BASE}/control`),
      ]);

      const fData = await parseJsonOrNull<ForecastResponse>(fRes);
      const oData = await parseJsonOrNull<OptionsResponse>(oRes);
      const sData = await parseJsonOrNull<SignalResponse>(sRes);
      const swarmData = await parseJsonOrNull<SwarmResponse>(swarmRes);
      const perfData = await parseJsonOrNull<PerformanceResponse>(perfRes);
      const backtestData = await parseJsonOrNull<BacktestResponse>(backtestRes);
      const portfolioData = await parseJsonOrNull<PortfolioResponse>(portfolioRes);
      const controlData = await parseJsonOrNull<ControlResponse>(controlRes);

      setForecast(fData);
      setOptions(oData);
      setSignal(sData);
      setSwarm(swarmData);
      setPerformance(perfData);
      setBacktest(backtestData);
      setPortfolio(portfolioData);
      setControl(controlData);
    }

    fetchAll().catch((error: unknown) => {
      console.error("Failed to fetch dashboard data", error);
    });
  }, [symbol]);

  async function handleToggleKillSwitch(enabled: boolean) {
    await fetch(`${API_BASE}/control/kill-switch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trading_enabled: enabled }),
    });

    const controlRes = await fetch(`${API_BASE}/control`);
    const controlData = (await controlRes.json()) as ControlResponse;
    setControl(controlData);
  }

  return (
    <main className="min-h-screen p-4 md:p-6">
      <div className="mb-4 flex items-center justify-between rounded-xl border border-terminal-line bg-terminal-panel/70 px-4 py-3">
        <h1 className="text-lg font-semibold md:text-2xl">GHOST ALPHA TERMINAL</h1>
        <span className="text-xs text-slate-300">
          Regime: {swarm?.regime ?? "..."} ({Math.round((swarm?.regime_confidence ?? 0) * 100)}%)
        </span>
      </div>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[220px_1fr_320px]">
        <aside className="panel rounded-xl p-4">
          <h2 className="mb-3 text-sm font-semibold text-terminal-accent">Watchlist</h2>
          <div className="space-y-2">
            {watchlist.map((item) => (
              <button
                key={item}
                onClick={() => setSymbol(item)}
                className={`w-full rounded border px-3 py-2 text-left text-sm transition ${
                  symbol === item
                    ? "border-terminal-accent bg-terminal-accent/15 text-terminal-accent"
                    : "border-terminal-line bg-black/20 text-slate-300 hover:border-terminal-accent/50"
                }`}
              >
                {item}
              </button>
            ))}
          </div>
        </aside>

        <div className="space-y-4">
          <Chart
            symbol={symbol}
            currentPrice={options?.underlying_price ?? 100}
            forecastPrices={forecast?.forecast_prices ?? []}
          />
          <OptionsPanel options={options} />
          <AgentPanel swarm={swarm} />
          <SwarmVisualizationPanel
            symbol={symbol}
            regime={swarm?.regime ?? "RANGE_BOUND"}
            regimeConfidence={swarm?.regime_confidence ?? 0.5}
            forecastPrices={forecast?.forecast_prices ?? []}
            currentPrice={options?.underlying_price ?? 100}
          />
          <PerformancePanel performance={performance} />
          <BacktestPanel backtest={backtest} />
        </div>

        <aside className="space-y-4">
          <ForecastPanel forecast={forecast} />
          <SignalPanel signal={signal} />
          <div className="panel rounded-xl p-4 text-sm text-slate-300">
            <h3 className="mb-3 text-sm font-semibold text-terminal-accent">AI Insights</h3>
            <p>
              Regime: {forecast?.volatility ?? "..."} volatility. Directional bias: {forecast?.direction ?? "..."}.
              Strategy engine prefers {signal?.signal ?? "..."}, while swarm consensus is{" "}
              {swarm?.consensus?.top_strategy ?? "..."}. Suggested size {swarm?.position_size ?? 0} with {" "}
              {swarm?.risk_level ?? "MEDIUM"} risk.
            </p>
          </div>
          <PortfolioPanel portfolio={portfolio} />
          <ControlPanel control={control} onToggleKillSwitch={handleToggleKillSwitch} />
        </aside>
      </section>
    </main>
  );
}
