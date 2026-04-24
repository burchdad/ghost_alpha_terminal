"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

import AgentPanel from "../../components/AgentPanel";
import BacktestPanel from "../../components/BacktestPanel";
import CandlestickChart from "../../components/CandlestickChart";
import Chart from "../../components/Chart";
import ExecutionHistoryPanel from "../../components/ExecutionHistoryPanel";
import ForecastPanel from "../../components/ForecastPanel";
import OpportunityFeedPanel from "../../components/OpportunityFeedPanel";
import OptionsPanel from "../../components/OptionsPanel";
import PerformancePanel from "../../components/PerformancePanel";
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
  const [symbolFilter, setSymbolFilter] = useState("");
  const [rightSidebarTab, setRightSidebarTab] = useState<"insights" | "history">("insights");
  const [selectedBroker, setSelectedBroker] = useState<string | null>(null);
  const [forecast, setForecast] = useState<ForecastResponse | null>(null);
  const [options, setOptions] = useState<OptionsResponse | null>(null);
  const [signal, setSignal] = useState<SignalResponse | null>(null);
  const [swarm, setSwarm] = useState<SwarmResponse | null>(null);
  const [performance, setPerformance] = useState<PerformanceResponse | null>(null);
  const [opportunities, setOpportunities] = useState<OpportunitiesResponse | null>(null);
  const [executionHistory, setExecutionHistory] = useState<ExecutionHistoryEntry[] | null>(null);
  const [orchestratorWatchlist, setOrchestratorWatchlist] = useState<string[]>([]);
  const [universeFallback, setUniverseFallback] = useState<string[]>([]);
  const [dataHealth, setDataHealth] = useState<string[]>([]);
  const [refreshing, setRefreshing] = useState(false);

  const watchlist = useMemo(() => {
    const ranked = opportunities?.opportunities ?? [];
    const topOpportunities = ranked.slice(0, 60).map((item) => item.symbol);
    const fallback = universeFallback.length > 0
      ? universeFallback
      : [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "SPY", "QQQ", "IWM",
        "AMD", "NFLX", "AVGO", "PLTR", "SMCI", "TSM", "INTC", "MU", "CRM", "ORCL",
        "JPM", "BAC", "XLF", "XLE", "GLD", "SLV", "TLT", "BTCUSD", "ETHUSD", "COIN",
      ];
    return Array.from(new Set([symbol, ...orchestratorWatchlist, ...topOpportunities, ...fallback])).slice(0, 180);
  }, [opportunities, symbol, orchestratorWatchlist, universeFallback]);

  const filteredWatchlist = useMemo(() => {
    const query = symbolFilter.trim().toUpperCase();
    if (!query) {
      return watchlist;
    }
    return watchlist.filter((item) => item.includes(query));
  }, [watchlist, symbolFilter]);

  useEffect(() => {
    async function hydrateWatchlist() {
      // Fetch dynamic universe as fallback base (runs in background, non-blocking).
      fetch(`${API_BASE}/universe/symbols`)
        .then((r) => r.ok ? r.json() : null)
        .then((data: { symbols?: string[] } | null) => {
          if (data?.symbols?.length) {
            setUniverseFallback(data.symbols.slice(0, 300));
          }
        })
        .catch(() => { /* silent — static seed stays active */ });

      // Reuse orchestrator rankings for a broader, high-signal watchlist without re-adding orchestrator UI.
      const latestRes = await fetch(`${API_BASE}/orchestrator/scan/latest`);
      const latest = await parseJsonOrNull<OrchestratorScanLite>(latestRes);
      if (latest?.candidates?.length) {
        setOrchestratorWatchlist(latest.candidates.slice(0, 120).map((c) => c.symbol));
      } else {
        // Keep startup resilient during scan outages by skipping active scan requests.
        setOrchestratorWatchlist([]);
      }
    }

    hydrateWatchlist().catch((error: unknown) => {
      console.error("Failed to hydrate terminal watchlist", error);
    });
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const params = new URLSearchParams(window.location.search);
    const qpSymbol = (params.get("symbol") ?? "").toUpperCase();
    const qpBroker = (params.get("broker") ?? "").toLowerCase();
    if (qpSymbol) {
      setSymbol(qpSymbol);
    }
    if (qpBroker) {
      setSelectedBroker(qpBroker);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const url = new URL(window.location.href);
    url.searchParams.set("symbol", symbol);
    if (selectedBroker) {
      url.searchParams.set("broker", selectedBroker);
    } else {
      url.searchParams.delete("broker");
    }
    window.history.replaceState({}, "", url.toString());
  }, [selectedBroker, symbol]);

  const fetchAll = useCallback(async () => {
    setRefreshing(true);
    const warnings: string[] = [];
    const [
      fRes,
      oRes,
      sRes,
      swarmRes,
      perfRes,
    ] = await Promise.all([
      fetch(`${API_BASE}/forecast/${symbol}`),
      fetch(`${API_BASE}/options/${symbol}`),
      fetch(`${API_BASE}/signal/${symbol}`),
      fetch(`${API_BASE}/swarm/${symbol}`),
      fetch(`${API_BASE}/performance/${symbol}`),
    ]);

    const fData = await parseJsonOrNull<ForecastResponse>(fRes);
    const oData = await parseJsonOrNull<OptionsResponse>(oRes);
    const sData = await parseJsonOrNull<SignalResponse>(sRes);
    const swarmData = await parseJsonOrNull<SwarmResponse>(swarmRes);
    const perfData = await parseJsonOrNull<PerformanceResponse>(perfRes);

    if (!fRes.ok) warnings.push(`Forecast ${fRes.status}`);
    if (!oRes.ok) warnings.push(`Options ${oRes.status}`);
    if (!sRes.ok) warnings.push(`Signal ${sRes.status}`);
    if (!swarmRes.ok) warnings.push(`Swarm ${swarmRes.status}`);
    if (!perfRes.ok) warnings.push(`Performance ${perfRes.status}`);

    setForecast(fData);
    setOptions(oData);
    setSignal(sData);
    setSwarm(swarmData);
    setPerformance(perfData);
    setDataHealth((prev) => {
      const nonSymbolWarnings = prev.filter((item) => item.startsWith("Opportunities") || item.startsWith("History"));
      return [...nonSymbolWarnings, ...warnings];
    });
    setRefreshing(false);
  }, [symbol]);

  useEffect(() => {
    fetchAll().catch((error: unknown) => {
      console.error("Failed to fetch terminal data", error);
      setRefreshing(false);
      setDataHealth((prev) => [...prev.filter((item) => item.startsWith("Opportunities") || item.startsWith("History")), "Terminal fetch failed"]);
    });
  }, [fetchAll]);

  useEffect(() => {
    let cancelled = false;

    async function fetchGlobalPanels() {
      const warnings: string[] = [];
      try {
        const [oppRes, historyRes] = await Promise.all([
          fetch(`${API_BASE}/agents/opportunities?limit=10`),
          fetch(`${API_BASE}/agents/execution-history?limit=25`),
        ]);

        if (!oppRes.ok) warnings.push(`Opportunities ${oppRes.status}`);
        if (!historyRes.ok) warnings.push(`History ${historyRes.status}`);

        const oppData = await parseJsonOrNull<OpportunitiesResponse>(oppRes);
        const historyData = await parseJsonOrNull<ExecutionHistoryResponse>(historyRes);

        if (!cancelled) {
          if (oppData) {
            setOpportunities(oppData);
          }
          if (historyData) {
            setExecutionHistory(historyData.executions ?? []);
          }
          setDataHealth((prev) => {
            const symbolWarnings = prev.filter(
              (item) =>
                item.startsWith("Forecast")
                || item.startsWith("Options")
                || item.startsWith("Signal")
                || item.startsWith("Swarm")
                || item.startsWith("Performance")
                || item === "Terminal fetch failed",
            );
            return [...symbolWarnings, ...warnings];
          });
        }
      } catch {
        if (!cancelled) {
          setDataHealth((prev) => {
            const symbolWarnings = prev.filter(
              (item) =>
                item.startsWith("Forecast")
                || item.startsWith("Options")
                || item.startsWith("Signal")
                || item.startsWith("Swarm")
                || item.startsWith("Performance")
                || item === "Terminal fetch failed",
            );
            return [...symbolWarnings, "Opportunities/History fetch failed"];
          });
        }
      }
    }

    void fetchGlobalPanels();
    const interval = setInterval(() => {
      void fetchGlobalPanels();
    }, 90000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return (
    <main className="min-h-screen px-5 pt-5 pb-8 md:px-8 md:pt-6">
      <header className="mb-6 border-b border-terminal-line pb-5">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="text-[9px] font-bold uppercase tracking-widest text-terminal-accent">Ghost Alpha</div>
            <h1 className="text-lg font-semibold text-slate-100 md:text-2xl">Deep Terminal</h1>
            <p className="mt-1 text-xs text-slate-400">Expanded symbol universe with fast picker and live execution intelligence.</p>
          </div>
          <div className="flex flex-wrap gap-2 text-[11px]">
            <span className="rounded-full border border-terminal-line bg-terminal-panel/60 px-3 py-1 text-slate-300">
              {selectedBroker ? selectedBroker.toUpperCase() : "All Brokers"}
            </span>
            <span className="rounded-full border border-terminal-line bg-terminal-panel/60 px-3 py-1 text-terminal-accent">
              {symbol}
            </span>
            <span className="rounded-full border border-terminal-line bg-terminal-panel/60 px-3 py-1 text-slate-300">
              {swarm?.regime ?? "..."} ({Math.round((swarm?.regime_confidence ?? 0) * 100)}%)
            </span>
            <span className={`rounded-full border px-3 py-1 ${refreshing ? "border-amber-500/60 bg-amber-500/10 text-amber-200" : "border-terminal-line bg-terminal-panel/60 text-slate-300"}`}>
              {refreshing ? "Refreshing" : "Live"}
            </span>
          </div>
        </div>
      </header>

      {selectedBroker && (
        <div className="mb-4 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
          Broker-aware deep mode active: {selectedBroker.toUpperCase()}. Market/strategy panes remain full-system, while execution context follows broker selection from Alpha.
        </div>
      )}

      {dataHealth.length > 0 && (
        <div className="mb-4 rounded-xl border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span>Data stream warnings: {dataHealth.join(" · ")}</span>
            <button
              type="button"
              onClick={() => void fetchAll()}
              className="rounded border border-amber-500/50 px-2 py-1 text-[11px] hover:bg-amber-500/20"
            >
              Retry Symbol Feeds
            </button>
          </div>
        </div>
      )}

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[240px_minmax(0,1fr)_340px]">
        <aside className="flex flex-col gap-3">
          <div className="overflow-hidden rounded-xl border border-terminal-line bg-terminal-panel/70">
            <div className="border-b border-terminal-line px-4 py-3">
              <div className="text-[9px] font-semibold uppercase tracking-widest text-slate-500">Symbol Controls</div>
              <div className="text-sm font-semibold text-terminal-accent">Watchlist</div>
              <div className="mt-1 text-[11px] text-slate-400">{watchlist.length} symbols available</div>
            </div>
            <div className="space-y-3 p-3">
              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-500" htmlFor="symbol-filter">
                  Filter
                </label>
                <input
                  id="symbol-filter"
                  value={symbolFilter}
                  onChange={(event) => setSymbolFilter(event.target.value.toUpperCase())}
                  placeholder="Search symbol"
                  className="w-full rounded border border-terminal-line bg-black/20 px-2 py-1.5 text-xs text-slate-200 outline-none focus:border-terminal-accent"
                />
              </div>
              <div>
                <label className="mb-1 block text-[10px] font-semibold uppercase tracking-wider text-slate-500" htmlFor="symbol-select">
                  Dropdown Picker
                </label>
                <select
                  id="symbol-select"
                  value={symbol}
                  onChange={(event) => setSymbol(event.target.value)}
                  className="w-full rounded border border-terminal-line bg-black/20 px-2 py-1.5 text-xs text-slate-200 outline-none focus:border-terminal-accent"
                >
                  {filteredWatchlist.slice(0, 200).map((item) => (
                    <option key={item} value={item}>
                      {item}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3">
            <div className="mb-2 text-[10px] font-semibold uppercase tracking-wider text-slate-500">Quick Picks</div>
            <div className="max-h-[64vh] space-y-2 overflow-y-auto pr-1">
              {filteredWatchlist.length === 0 && (
                <div className="rounded border border-terminal-line bg-black/20 px-2 py-2 text-xs text-slate-400">No symbols match the current filter.</div>
              )}
              {filteredWatchlist.slice(0, 120).map((item) => (
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
          </div>
        </aside>

        <div className="space-y-4">
          <CandlestickChart symbol={symbol} days={90} signalLabel={signal?.signal ?? null} />
          <Chart
            symbol={symbol}
            forecastPrices={forecast?.forecast_prices ?? []}
          />
          <OptionsPanel
            options={options}
            symbol={symbol}
            onStrategyExecuted={() => {
              void fetchAll();
            }}
          />
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

        <aside className="flex flex-col gap-3">
          <div className="overflow-hidden rounded-xl border border-terminal-line bg-terminal-panel/70">
            <div className="flex">
              {(
                [
                  { id: "insights", label: "Insights" },
                  { id: "history", label: "History" },
                ] as const
              ).map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => setRightSidebarTab(tab.id)}
                  className={`flex-1 py-2.5 text-xs font-medium transition ${
                    rightSidebarTab === tab.id
                      ? "border-b-2 border-terminal-accent text-terminal-accent"
                      : "border-b-2 border-transparent text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {rightSidebarTab === "insights" && (
            <>
              <ForecastPanel forecast={forecast} />
              <SignalPanel signal={signal} />
              <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4 text-sm text-slate-300">
                <h3 className="mb-3 text-sm font-semibold text-terminal-accent">AI Insights</h3>
                <p>
                  Regime: {forecast?.volatility ?? "..."} volatility. Directional bias: {forecast?.direction ?? "..."}.
                  Strategy engine prefers {signal?.signal ?? "..."}, while swarm consensus is {" "}
                  {swarm?.consensus?.top_strategy ?? "..."}. Suggested size {swarm?.position_size ?? 0} with {" "}
                  {swarm?.risk_level ?? "MEDIUM"} risk.
                </p>
              </div>
            </>
          )}

          {rightSidebarTab === "history" && (
            <ExecutionHistoryPanel history={executionHistory} />
          )}
        </aside>
      </section>
    </main>
  );
}
