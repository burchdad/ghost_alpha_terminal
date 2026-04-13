"use client";

import { useEffect, useMemo, useState } from "react";

import AgentPanel from "../../components/AgentPanel";
import BacktestPanel from "../../components/BacktestPanel";
import CandlestickChart from "../../components/CandlestickChart";
import Chart from "../../components/Chart";
import DashboardCopilot from "../../components/DashboardCopilot";
import ExecutionHistoryPanel from "../../components/ExecutionHistoryPanel";
import ForecastPanel from "../../components/ForecastPanel";
import OpportunityFeedPanel from "../../components/OpportunityFeedPanel";
import OptionsPanel from "../../components/OptionsPanel";
import PerformancePanel from "../../components/PerformancePanel";
import SignalPanel from "../../components/SignalPanel";
import SwarmVisualizationPanel from "../../components/swarm/SwarmVisualizationPanel";
import { apiFetch } from "../../lib/apiClient";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type ForecastResponse = {
  symbol: string;
  direction: "UP" | "DOWN" | "SIDEWAYS";
  confidence: number;
  volatility: "LOW" | "MEDIUM" | "HIGH";
  range_bound: boolean;
  forecast_prices: number[];
  timeframe?: string;
  generated_at?: string;
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

type GoalStatusResponse = {
  enabled: boolean;
  start_capital: number | null;
  target_capital: number | null;
  timeframe_days: number | null;
  elapsed_days: number;
  remaining_days: number | null;
  required_total_return: number;
  required_daily_return: number;
  required_daily_return_remaining: number;
  trajectory_expected_capital: number | null;
  trajectory_gap_pct: number;
  goal_pressure_multiplier: number;
  success_probability: number;
  stress_level: "LOW" | "MEDIUM" | "HIGH" | "EXTREME";
  target_unrealistic: boolean;
  suggested_target_capital: number | null;
  suggested_timeframe_days: number | null;
  message: string;
};

type OpportunityRecommendation = {
  symbol: string;
  asset_class: string;
  region: string;
  regime: string;
  signal: string;
  consensus_bias: string;
  consensus_confidence: number;
  expected_return_pct: number;
  expected_value: number;
  risk_level: string;
  target_pct: number;
  recommended_notional: number;
  tradable: boolean;
  risk_adjusted_score: number;
  signal_validation?: {
    validated_signal_strength?: number;
    confirmation_count?: number;
  };
  market_reaction?: {
    correlation_score?: number;
  };
};

type CapitalSplitRecommendation = {
  symbol: string;
  recommended_notional: number;
  allocation_weight: number;
};

type OpportunitiesResponse = {
  scanned: number;
  passed_prefilter: number;
  opportunities: OpportunityRecommendation[];
  capital_allocation_recommendations: CapitalSplitRecommendation[];
  goal: GoalStatusResponse;
};

type ExecutionHistoryEntry = {
  execution_id: string;
  cycle_id: string;
  symbol: string;
  regime: string;
  action: string;
  strategy: string;
  confidence: number;
  risk_level: string;
  allocation_pct: number;
  qty: number;
  notional: number;
  mode: string;
  submitted: boolean;
  order_id: string | null;
  reason: string;
  error: string | null;
  timestamp: string;
  outcome_label: string | null;
  pnl: number | null;
};

type ExecutionHistoryResponse = {
  executions: ExecutionHistoryEntry[];
};

type OrchestratorScanLite = {
  candidates: Array<{ symbol: string }>;
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

export default function TerminalPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [options, setOptions] = useState<OptionsResponse | null>(null);
  const [signal, setSignal] = useState<SignalResponse | null>(null);
  const [swarm, setSwarm] = useState<SwarmResponse | null>(null);
  const [performance, setPerformance] = useState<PerformanceResponse | null>(null);
  const [opportunities, setOpportunities] = useState<OpportunitiesResponse | null>(null);
  const [executionHistory, setExecutionHistory] = useState<ExecutionHistoryEntry[] | null>(null);
  const [orchestratorWatchlist, setOrchestratorWatchlist] = useState<string[]>([]);
  const [universeFallback, setUniverseFallback] = useState<string[]>([]);

  const watchlist = useMemo(() => {
    const ranked = opportunities?.opportunities ?? [];
    const topOpportunities = ranked.slice(0, 25).map((item) => item.symbol);
    const fallback = universeFallback.length > 0
      ? universeFallback
      : ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "SPY", "QQQ", "IWM"];
    return Array.from(new Set([symbol, ...orchestratorWatchlist, ...topOpportunities, ...fallback])).slice(0, 50);
  }, [opportunities, symbol, orchestratorWatchlist, universeFallback]);

  useEffect(() => {
    async function hydrateWatchlist() {
      // Fetch dynamic universe as fallback base (runs in background, non-blocking).
      fetch(`${API_BASE}/universe/symbols`)
        .then((r) => r.ok ? r.json() : null)
        .then((data: { symbols?: string[] } | null) => {
          if (data?.symbols?.length) {
            setUniverseFallback(data.symbols.slice(0, 100));
          }
        })
        .catch(() => { /* silent — static seed stays active */ });

      // Reuse orchestrator rankings for a broader, high-signal watchlist without re-adding orchestrator UI.
      const latestRes = await fetch(`${API_BASE}/orchestrator/scan/latest`);
      const latest = await parseJsonOrNull<OrchestratorScanLite>(latestRes);
      if (latest?.candidates?.length) {
        setOrchestratorWatchlist(latest.candidates.slice(0, 50).map((c) => c.symbol));
        return;
      }

      const scanRes = await apiFetch(`${API_BASE}/orchestrator/scan?limit=15`, {
        apiBase: API_BASE,
        method: "POST",
      });
      const scan = await parseJsonOrNull<OrchestratorScanLite>(scanRes);
      setOrchestratorWatchlist((scan?.candidates ?? []).slice(0, 30).map((c) => c.symbol));
    }

    hydrateWatchlist().catch((error: unknown) => {
      console.error("Failed to hydrate terminal watchlist", error);
    });
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const qpSymbol = (new URLSearchParams(window.location.search).get("symbol") ?? "").toUpperCase();
    if (qpSymbol) {
      setSymbol(qpSymbol);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const url = new URL(window.location.href);
    url.searchParams.set("symbol", symbol);
    window.history.replaceState({}, "", url.toString());
  }, [symbol]);

  useEffect(() => {
    async function fetchAll() {
      const [
        fRes,
        oRes,
        sRes,
        swarmRes,
        perfRes,
        oppRes,
        historyRes,
      ] = await Promise.all([
        fetch(`${API_BASE}/forecast/${symbol}`),
        fetch(`${API_BASE}/options/${symbol}`),
        fetch(`${API_BASE}/signal/${symbol}`),
        fetch(`${API_BASE}/swarm/${symbol}`),
        fetch(`${API_BASE}/performance/${symbol}`),
        fetch(`${API_BASE}/agents/opportunities?limit=10`),
        fetch(`${API_BASE}/agents/execution-history?limit=25`),
      ]);

      const fData = await parseJsonOrNull<ForecastResponse>(fRes);
      const oData = await parseJsonOrNull<OptionsResponse>(oRes);
      const sData = await parseJsonOrNull<SignalResponse>(sRes);
      const swarmData = await parseJsonOrNull<SwarmResponse>(swarmRes);
      const perfData = await parseJsonOrNull<PerformanceResponse>(perfRes);
      const oppData = await parseJsonOrNull<OpportunitiesResponse>(oppRes);
      const historyData = await parseJsonOrNull<ExecutionHistoryResponse>(historyRes);

      setForecast(fData);
      setOptions(oData);
      setSignal(sData);
      setSwarm(swarmData);
      setPerformance(perfData);
      setOpportunities(oppData);
      setExecutionHistory(historyData?.executions ?? []);
    }

    fetchAll().catch((error: unknown) => {
      console.error("Failed to fetch terminal data", error);
    });
  }, [symbol]);

  return (
    <main className="min-h-screen p-4 md:p-6">
      <div className="mb-4 flex items-center justify-between rounded-xl border border-terminal-line bg-terminal-panel/70 px-4 py-3">
        <h1 className="text-lg font-semibold md:text-2xl">DEEP TERMINAL</h1>
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
          <CandlestickChart symbol={symbol} days={90} signalLabel={signal?.signal ?? null} />
          <Chart
            symbol={symbol}
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
          <BacktestPanel symbol={symbol} />
          <OpportunityFeedPanel data={opportunities} />
        </div>

        <aside className="space-y-4">
          <ForecastPanel forecast={forecast} />
          <SignalPanel signal={signal} />
          <div className="panel rounded-xl p-4 text-sm text-slate-300">
            <h3 className="mb-3 text-sm font-semibold text-terminal-accent">AI Insights</h3>
            <p>
              Regime: {forecast?.volatility ?? "..."} volatility. Directional bias: {forecast?.direction ?? "..."}.
              Strategy engine prefers {signal?.signal ?? "..."}, while swarm consensus is {" "}
              {swarm?.consensus?.top_strategy ?? "..."}. Suggested size {swarm?.position_size ?? 0} with {" "}
              {swarm?.risk_level ?? "MEDIUM"} risk.
            </p>
          </div>
          <ExecutionHistoryPanel history={executionHistory} />
        </aside>
      </section>

      <section className="mt-6 rounded-xl border border-terminal-line bg-terminal-panel/70 p-4">
        <DashboardCopilot />
      </section>
    </main>
  );
}
