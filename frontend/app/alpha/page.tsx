"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import ControlPanel from "../../components/ControlPanel";
import ContextPanel from "../../components/ContextPanel";
import DecisionAuditPanel from "../../components/DecisionAuditPanel";
import DecisionReplayPanel from "../../components/DecisionReplayPanel";
import GoalPanel from "../../components/GoalPanel";
import NewsPanel from "../../components/NewsPanel";
import OrchestratorPanel, {
  type OrchestratorScan,
  type OrchestratorStatus,
} from "../../components/OrchestratorPanel";
import PortfolioPanel from "../../components/PortfolioPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

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
  strategy_exposure: Record<string, number>;
  available_buying_power: number;
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
  autonomous_enabled: boolean;
  autonomous_interval_seconds: number;
  autonomous_symbols: string[];
  autonomous_cycles_run: number;
  autonomous_last_run_at: string | null;
  autonomous_last_error: string | null;
};

type ExecutionModeResponse = {
  mode: "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING";
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

type ContextSignalResponse = {
  symbol: string;
  data_classification: "PUBLIC" | "DERIVED" | "RESTRICTED" | "UNKNOWN";
  sources_used: string[];
  sentiment_score: number;
  news_momentum_score: number;
  event_strength: number;
  event_flags: string[];
  signal_validation: {
    recency_decay_factor: number;
    average_source_weight: number;
    confirmation_count: number;
    confirmation_factor: number;
    confirmation_label: string;
    validated_signal_strength: number;
    source_details: Array<{
      source: string;
      source_weight: number;
      age_hours: number;
      decay_factor: number;
      effective_weight: number;
    }>;
  };
  market_reaction: {
    price_reaction_pct: number;
    volume_spike_ratio: number;
    breakout: string;
    expected_direction: string;
    price_direction: string;
    correlation_score: number;
    actionability_multiplier: number;
  };
  modifiers: {
    confidence_modifier: number;
    risk_modifier: number;
    opportunity_boost: number;
  };
  rationale: string;
};

type NewsSignalResponse = {
  symbol: string;
  timestamp: string;
  data_classification: "PUBLIC" | "DERIVED" | "RESTRICTED" | "UNKNOWN";
  sources_used: string[];
  sentiment_score: number;
  news_momentum_score: number;
  event_strength: number;
  event_flags: string[];
  rationale: string;
};

type NewsAuditEntry = {
  timestamp: string;
  symbol: string;
  data_classification: "PUBLIC" | "DERIVED" | "RESTRICTED" | "UNKNOWN";
  sources_used: string[];
  sentiment_score: number;
  news_momentum_score: number;
  event_strength: number;
  event_flags: string[];
};

type NewsAuditResponse = {
  entries: NewsAuditEntry[];
};

type DecisionAuditSummary = {
  audit_id: string;
  timestamp: string;
  decision_type: string;
  symbol: string;
  status: string;
  cycle_id: string | null;
};

type DecisionAuditSummaryListResponse = {
  entries: DecisionAuditSummary[];
};

type DecisionReplayStep = {
  stage: string;
  title: string;
  summary: string;
  payload: Record<string, unknown>;
};

type DecisionReplayResponse = {
  audit_id: string;
  symbol: string;
  decision_type: string;
  status: string;
  generated_at: string;
  replay_steps: DecisionReplayStep[];
  why_not: string[];
};

type AlpacaOauthStatusResponse = {
  provider: "alpaca";
  connected: boolean;
  permissions: string;
  paper_mode: boolean;
  mode: "Paper Trading" | "Live Trading";
  token_type: string | null;
  scope: string | null;
  obtained_at: string | null;
  expires_in: number | null;
  updated_at: string | null;
  oauth_ready: boolean;
};

type LightweightMetricsResponse = {
  window_days: number;
  scans_run: number;
  trades_triggered: number;
  top_strategies: Array<{ strategy: string; count: number }>;
};

type ExecutionHistoryEntry = {
  execution_id: string;
  cycle_id: string | null;
  symbol: string;
  action: string;
  mode: string;
  submitted: boolean;
  order_id: string | null;
  reason: string | null;
  error: string | null;
  timestamp: string;
};

type ExecutionHistoryResponse = {
  entries: ExecutionHistoryEntry[];
};

type RuntimeToast = {
  id: string;
  tone: "success" | "warning" | "error";
  message: string;
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

export default function AlphaPage() {
  const [scan, setScan] = useState<OrchestratorScan | null>(null);
  const [status, setStatus] = useState<OrchestratorStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [focusSymbol, setFocusSymbol] = useState("AAPL");

  const [portfolio, setPortfolio] = useState<PortfolioResponse | null>(null);
  const [control, setControl] = useState<ControlResponse | null>(null);
  const [executionMode, setExecutionMode] = useState<ExecutionModeResponse["mode"] | null>(null);
  const [goal, setGoal] = useState<GoalStatusResponse | null>(null);
  const [contextSignal, setContextSignal] = useState<ContextSignalResponse | null>(null);
  const [newsSignal, setNewsSignal] = useState<NewsSignalResponse | null>(null);
  const [newsAudit, setNewsAudit] = useState<NewsAuditEntry[] | null>(null);
  const [decisionAudit, setDecisionAudit] = useState<DecisionAuditSummary[] | null>(null);
  const [selectedAuditId, setSelectedAuditId] = useState<string | null>(null);
  const [decisionReplay, setDecisionReplay] = useState<DecisionReplayResponse | null>(null);
  const [oauthStatus, setOauthStatus] = useState<"idle" | "connected" | "error">("idle");
  const [oauthReason, setOauthReason] = useState<string>("");
  const [brokerConnection, setBrokerConnection] = useState<AlpacaOauthStatusResponse | null>(null);
  const [disconnecting, setDisconnecting] = useState(false);
  const [launchMetrics, setLaunchMetrics] = useState<LightweightMetricsResponse | null>(null);
  const [runtimeToasts, setRuntimeToasts] = useState<RuntimeToast[]>([]);
  const seenExecutionIdsRef = useRef<Set<string>>(new Set());
  const executionBaselineReadyRef = useRef(false);
  const autonomousCycleBaselineRef = useRef<number | null>(null);

  const strategyCounts = useMemo(() => {
    const counts: Record<string, number> = {
      OPTIONS_PLAY: 0,
      SWING_TRADE: 0,
      DAY_TRADE: 0,
      SCALP: 0,
      WATCH: 0,
      IGNORE: 0,
    };
    for (const c of scan?.candidates ?? []) {
      counts[c.strategy_type] = (counts[c.strategy_type] ?? 0) + 1;
    }
    return counts;
  }, [scan]);

  const topSymbols = useMemo(() => {
    return (scan?.candidates ?? []).slice(0, 12).map((c) => c.symbol);
  }, [scan]);

  const wowTopThree = useMemo(() => {
    return (scan?.candidates ?? []).slice(0, 3);
  }, [scan]);

  const compactStats = useMemo(() => {
    const executionReady = (scan?.candidates ?? []).filter((c) => c.action_label === "EXECUTE").length;
    const highConviction = (scan?.candidates ?? []).filter((c) => c.composite_score >= 0.7).length;
    const openPositions = portfolio?.active_positions.length ?? 0;
    const exposurePct = (portfolio?.risk_exposure_pct ?? 0) * 100;
    const drawdownPct = (control?.rolling_drawdown_pct ?? 0) * 100;
    const riskBudgetLeft = Math.max(0, ((control?.daily_loss_limit ?? 0) - (control?.daily_loss ?? 0)));
    const stress = goal?.stress_level ?? "LOW";
    const goalProb = (goal?.success_probability ?? 0) * 100;
    const newsStrength = newsSignal?.event_strength ?? 0;
    const contextConfidence = contextSignal?.modifiers.confidence_modifier ?? 1;
    const audits = decisionAudit ?? [];
    const accepted = audits.filter((a) => a.status === "ACCEPTED").length;
    return {
      executionReady,
      highConviction,
      openPositions,
      exposurePct,
      drawdownPct,
      riskBudgetLeft,
      stress,
      goalProb,
      newsStrength,
      contextConfidence,
      audits: audits.length,
      accepted,
    };
  }, [scan, portfolio, control, goal, newsSignal, contextSignal, decisionAudit]);

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }
    const qs = new URLSearchParams(window.location.search);
    const oauth = qs.get("alpaca_oauth");
    const reason = qs.get("reason") ?? "";
    if (oauth === "connected") {
      setOauthStatus("connected");
      setOauthReason("");
    } else if (oauth === "error") {
      setOauthStatus("error");
      setOauthReason(reason);
    }
  }, []);

  async function refreshBrokerConnection() {
    const brokerRes = await fetch(`${API_BASE}/alpaca/oauth/status`);
    const brokerData = await parseJsonOrNull<AlpacaOauthStatusResponse>(brokerRes);
    setBrokerConnection(brokerData);
  }

  async function refreshLaunchMetrics() {
    const metricsRes = await fetch(`${API_BASE}/metrics/lightweight?days=7`);
    const metricsData = await parseJsonOrNull<LightweightMetricsResponse>(metricsRes);
    setLaunchMetrics(metricsData);
  }

  function pushRuntimeToast(message: string, tone: RuntimeToast["tone"]) {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setRuntimeToasts((current) => [...current.slice(-2), { id, tone, message }]);
    window.setTimeout(() => {
      setRuntimeToasts((current) => current.filter((toast) => toast.id !== id));
    }, 6000);
  }

  async function refreshScanState(triggerScan = false) {
    const [statusRes, latestRes] = await Promise.all([
      fetch(`${API_BASE}/orchestrator/status`),
      fetch(`${API_BASE}/orchestrator/scan/latest`),
    ]);
    const statusData = await parseJsonOrNull<OrchestratorStatus>(statusRes);
    const latestData = await parseJsonOrNull<OrchestratorScan>(latestRes);
    setStatus(statusData);
    if (latestData) {
      setScan(latestData);
      return;
    }
    if (!triggerScan) {
      return;
    }
    setLoading(true);
    try {
      const scanRes = await fetch(`${API_BASE}/orchestrator/scan?limit=25`, { method: "POST" });
      const scanData = await parseJsonOrNull<OrchestratorScan>(scanRes);
      setScan(scanData);
      const refreshed = await fetch(`${API_BASE}/orchestrator/status`);
      const refreshedStatus = await parseJsonOrNull<OrchestratorStatus>(refreshed);
      setStatus(refreshedStatus);
    } finally {
      setLoading(false);
    }
  }

  async function refreshRuntimeState(announceExecutions = false) {
    const [portfolioRes, controlRes, executionModeRes, goalRes, historyRes] = await Promise.all([
      fetch(`${API_BASE}/portfolio`),
      fetch(`${API_BASE}/control`),
      fetch(`${API_BASE}/agents/execution-mode`),
      fetch(`${API_BASE}/agents/goal/status`),
      fetch(`${API_BASE}/agents/execution-history?limit=10`),
    ]);

    const portfolioData = await parseJsonOrNull<PortfolioResponse>(portfolioRes);
    const controlData = await parseJsonOrNull<ControlResponse>(controlRes);
    const executionModeData = await parseJsonOrNull<ExecutionModeResponse>(executionModeRes);
    const goalData = await parseJsonOrNull<GoalStatusResponse>(goalRes);
    const historyData = await parseJsonOrNull<ExecutionHistoryResponse>(historyRes);

    setPortfolio(portfolioData);
    setControl(controlData);
    setExecutionMode(executionModeData?.mode ?? null);
    setGoal(goalData);

    if (controlData) {
      if (autonomousCycleBaselineRef.current === null) {
        autonomousCycleBaselineRef.current = controlData.autonomous_cycles_run;
      } else if (announceExecutions && controlData.autonomous_cycles_run > autonomousCycleBaselineRef.current) {
        autonomousCycleBaselineRef.current = controlData.autonomous_cycles_run;
        pushRuntimeToast(`Autonomous cycle ${controlData.autonomous_cycles_run} completed.`, "success");
      } else {
        autonomousCycleBaselineRef.current = controlData.autonomous_cycles_run;
      }
    }

    if (!historyData) {
      return;
    }

    const latestEntries = historyData.entries ?? [];
    if (!executionBaselineReadyRef.current) {
      seenExecutionIdsRef.current = new Set(latestEntries.map((entry) => entry.execution_id));
      executionBaselineReadyRef.current = true;
      return;
    }

    if (!announceExecutions) {
      return;
    }

    for (const entry of [...latestEntries].reverse()) {
      if (seenExecutionIdsRef.current.has(entry.execution_id)) {
        continue;
      }
      seenExecutionIdsRef.current.add(entry.execution_id);
      if (entry.error) {
        pushRuntimeToast(`${entry.symbol} ${entry.action.toLowerCase()} failed: ${entry.error}`, "error");
      } else if (entry.submitted) {
        pushRuntimeToast(`${entry.symbol} ${entry.action.toLowerCase()} submitted in ${entry.mode.toLowerCase().replaceAll("_", " ")}.`, "success");
      } else {
        pushRuntimeToast(`${entry.symbol} ${entry.action.toLowerCase()} logged without broker submission.`, "warning");
      }
    }
  }

  async function refreshSymbolIntel(currentFocusSymbol: string, preferredAuditId: string | null = selectedAuditId) {
    const [contextRes, newsRes, newsAuditRes, auditRes] = await Promise.all([
      fetch(`${API_BASE}/agents/context/${currentFocusSymbol}`),
      fetch(`${API_BASE}/agents/news/${currentFocusSymbol}`),
      fetch(`${API_BASE}/agents/news/audit?limit=25`),
      fetch(`${API_BASE}/agents/audit/decisions?limit=25`),
    ]);

    const contextData = await parseJsonOrNull<ContextSignalResponse>(contextRes);
    const newsData = await parseJsonOrNull<NewsSignalResponse>(newsRes);
    const newsAuditData = await parseJsonOrNull<NewsAuditResponse>(newsAuditRes);
    const auditData = await parseJsonOrNull<DecisionAuditSummaryListResponse>(auditRes);

    setContextSignal(contextData);
    setNewsSignal(newsData);
    setNewsAudit(newsAuditData?.entries ?? []);

    const audits = auditData?.entries ?? [];
    setDecisionAudit(audits);
    const nextAuditId = preferredAuditId && audits.some((entry) => entry.audit_id === preferredAuditId)
      ? preferredAuditId
      : (audits[0]?.audit_id ?? null);
    setSelectedAuditId(nextAuditId);

    if (!nextAuditId) {
      setDecisionReplay(null);
      return;
    }

    const replayRes = await fetch(`${API_BASE}/agents/audit/replay/${nextAuditId}`);
    const replayData = await parseJsonOrNull<DecisionReplayResponse>(replayRes);
    setDecisionReplay(replayData);
  }

  useEffect(() => {
    async function boot() {
      await refreshScanState(true);
      await refreshRuntimeState(false);
      await refreshSymbolIntel(focusSymbol, selectedAuditId);
    }

    boot().catch((err: unknown) => {
      console.error("Failed to load alpha dashboard", err);
    });

    refreshBrokerConnection().catch((err: unknown) => {
      console.error("Failed to fetch broker connection status", err);
    });

    refreshLaunchMetrics().catch((err: unknown) => {
      console.error("Failed to fetch lightweight metrics", err);
    });
  }, []);

  useEffect(() => {
    Promise.all([
      refreshRuntimeState(false),
      refreshSymbolIntel(focusSymbol, selectedAuditId),
    ]).catch((error: unknown) => {
      console.error("Failed to fetch market operations data", error);
    });
  }, [focusSymbol, selectedAuditId]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      Promise.all([
        refreshRuntimeState(true),
        refreshScanState(false),
        refreshBrokerConnection(),
      ]).catch((error: unknown) => {
        console.error("Failed to poll live alpha dashboard state", error);
      });
    }, 10000);

    return () => {
      window.clearInterval(intervalId);
    };
  }, []);

  async function handleScan() {
    await refreshScanState(true);
    await refreshLaunchMetrics();
  }

  async function handleToggleAuto(enabled: boolean) {
    await fetch(`${API_BASE}/orchestrator/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auto_mode: enabled }),
    });
    const statusRes = await fetch(`${API_BASE}/orchestrator/status`);
    const statusData = await parseJsonOrNull<OrchestratorStatus>(statusRes);
    setStatus(statusData);
  }

  async function handleToggleKillSwitch(enabled: boolean) {
    await fetch(`${API_BASE}/control/kill-switch`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ trading_enabled: enabled }),
    });
    const controlRes = await fetch(`${API_BASE}/control`);
    const controlData = await parseJsonOrNull<ControlResponse>(controlRes);
    setControl(controlData);
    pushRuntimeToast(enabled ? "Trading re-enabled." : "Kill switch engaged.", enabled ? "success" : "warning");
  }

  async function handleToggleAutonomous(enabled: boolean) {
    await fetch(`${API_BASE}/control/autonomous`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    const controlRes = await fetch(`${API_BASE}/control`);
    const controlData = await parseJsonOrNull<ControlResponse>(controlRes);
    setControl(controlData);
    pushRuntimeToast(enabled ? "Autonomous execution enabled." : "Autonomous execution stopped.", enabled ? "success" : "warning");
  }

  async function handleRunAutonomousOnce() {
    await fetch(`${API_BASE}/control/autonomous/run-once`, { method: "POST" });
    await Promise.all([refreshRuntimeState(true), refreshScanState(false)]);
  }

  async function handleSetExecutionMode(mode: "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING") {
    await fetch(`${API_BASE}/agents/execution-mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode }),
    });
    const modeRes = await fetch(`${API_BASE}/agents/execution-mode`);
    const modeData = await parseJsonOrNull<ExecutionModeResponse>(modeRes);
    setExecutionMode(modeData?.mode ?? null);
    pushRuntimeToast(`Execution mode set to ${mode.replaceAll("_", " ").toLowerCase()}.`, "success");
  }

  async function handleSetGoal(payload: { start_capital: number; target_capital: number; timeframe_days: number }) {
    await fetch(`${API_BASE}/agents/goal`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const goalRes = await fetch(`${API_BASE}/agents/goal/status`);
    const goalData = await parseJsonOrNull<GoalStatusResponse>(goalRes);
    setGoal(goalData);
  }

  async function handleSelectAudit(auditId: string) {
    setSelectedAuditId(auditId);
    const replayRes = await fetch(`${API_BASE}/agents/audit/replay/${auditId}`);
    const replayData = await parseJsonOrNull<DecisionReplayResponse>(replayRes);
    setDecisionReplay(replayData);
  }

  function handleOrchestratorRunSymbol(symbol: string) {
    setFocusSymbol(symbol);
  }

  async function handleDisconnectAlpaca() {
    setDisconnecting(true);
    try {
      await fetch(`${API_BASE}/alpaca/oauth/disconnect`, { method: "POST" });
      setOauthStatus("idle");
      setOauthReason("");
      await Promise.all([refreshBrokerConnection(), refreshLaunchMetrics(), refreshRuntimeState(false)]);
      pushRuntimeToast("Alpaca connection removed.", "warning");
    } finally {
      setDisconnecting(false);
    }
  }

  const isConnected = Boolean(brokerConnection?.connected);
  const modeLabel = brokerConnection?.mode ?? "Paper Trading";
  const permissionsLabel = brokerConnection?.permissions ?? "Not Authorized";

  return (
    <main className="min-h-screen p-4 md:p-6">
      {runtimeToasts.length > 0 && (
        <div className="fixed right-4 top-4 z-50 flex w-[min(360px,calc(100vw-2rem))] flex-col gap-2">
          {runtimeToasts.map((toast) => (
            <div
              key={toast.id}
              className={`rounded-lg border px-3 py-2 text-xs shadow-lg backdrop-blur ${
                toast.tone === "success"
                  ? "border-green-500/40 bg-green-500/15 text-green-100"
                  : toast.tone === "warning"
                    ? "border-amber-500/40 bg-amber-500/15 text-amber-100"
                    : "border-red-500/40 bg-red-500/15 text-red-100"
              }`}
            >
              {toast.message}
            </div>
          ))}
        </div>
      )}
      <div className="mb-4 flex items-center justify-between rounded-xl border border-terminal-line bg-terminal-panel/70 px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold md:text-2xl">MARKET INTELLIGENCE DASHBOARD</h1>
          <p className="text-xs text-slate-400">Layer 1: Discovery and ranking across the full market universe</p>
        </div>
        <Link
          href="/terminal"
          className="rounded border border-terminal-line px-3 py-1.5 text-xs text-slate-300 hover:border-terminal-accent/50"
        >
          Open Deep Terminal
        </Link>
      </div>

      <section className="mb-4 rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-sm font-semibold text-terminal-accent">Connection Safety Banner</h2>
            <p className="text-xs text-slate-400">Transparent broker state and explicit user controls</p>
          </div>
          <div className="flex items-center gap-2">
            <a
              href={`${API_BASE}/alpaca/oauth/start?next=/alpha`}
              className="rounded border border-terminal-accent bg-terminal-accent/10 px-3 py-1.5 text-xs text-terminal-accent hover:bg-terminal-accent/20"
            >
              Connect Alpaca OAuth
            </a>
            <button
              type="button"
              disabled={!isConnected || disconnecting}
              onClick={handleDisconnectAlpaca}
              className="rounded border border-red-500/40 bg-red-500/10 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {disconnecting ? "Disconnecting..." : "Disconnect Alpaca"}
            </button>
          </div>
        </div>

        <div className={`mt-3 rounded border px-3 py-3 text-xs ${
          isConnected
            ? "border-green-500/40 bg-green-500/10 text-green-200"
            : "border-amber-500/40 bg-amber-500/10 text-amber-200"
        }`}>
          <div className="font-semibold">{isConnected ? "Connected to Alpaca" : "Not Connected to Alpaca"}</div>
          <div className="mt-1">Permissions: {permissionsLabel}</div>
          <div className="mt-1">Mode: {modeLabel}</div>
        </div>

        {oauthStatus !== "idle" && (
          <div
            className={`mt-3 rounded border px-3 py-2 text-xs ${
              oauthStatus === "connected"
                ? "border-green-500/40 bg-green-500/10 text-green-300"
                : "border-red-500/40 bg-red-500/10 text-red-300"
            }`}
          >
            {oauthStatus === "connected"
              ? "Alpaca OAuth connected successfully."
              : `Alpaca OAuth failed${oauthReason ? `: ${oauthReason}` : ""}`}
          </div>
        )}

        {isConnected && (
          <div className="mt-3 rounded border border-terminal-accent/40 bg-terminal-accent/10 px-3 py-3 text-xs text-terminal-accent">
            <div className="font-semibold">Top 3 Opportunities Right Now</div>
            {wowTopThree.length > 0 ? (
              <ul className="mt-2 space-y-1">
                {wowTopThree.map((candidate) => (
                  <li key={candidate.symbol}>
                    {candidate.symbol} {"->"} {candidate.strategy_type.replaceAll("_", " ")} ({Math.round(candidate.composite_score * 100)}%)
                  </li>
                ))}
              </ul>
            ) : (
              <div className="mt-2 text-slate-300">Run a market scan to generate your top opportunities.</div>
            )}
          </div>
        )}

        {launchMetrics && (
          <div className="mt-3 rounded border border-terminal-line bg-black/20 px-3 py-2 text-[11px] text-slate-300">
            Last {launchMetrics.window_days}d proof metrics: {launchMetrics.scans_run} scans, {launchMetrics.trades_triggered} trades, top strategy {launchMetrics.top_strategies[0]?.strategy ?? "N/A"}.
          </div>
        )}
      </section>

      <section className="sticky top-2 z-20 mb-4 rounded-xl border border-terminal-line bg-[#061723e6] p-3 backdrop-blur">
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-terminal-accent">NOC Strip</h2>
          <p className="text-[11px] text-slate-400">Compact market-wide telemetry</p>
        </div>
        <div className="flex gap-3 overflow-x-auto pb-1">
          <div className="min-w-[220px] rounded-lg border border-terminal-line bg-black/25 p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Ghost Alpha Engine</p>
            <p className="mt-1 text-sm font-semibold text-terminal-accent">
              {compactStats.executionReady} ready / {compactStats.highConviction} high conviction
            </p>
            <p className="text-[11px] text-slate-400">{scan?.total_scanned ?? 0} scanned</p>
          </div>

          <div className="min-w-[220px] rounded-lg border border-terminal-line bg-black/25 p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Portfolio</p>
            <p className="mt-1 text-sm font-semibold text-cyan-300">
              {compactStats.openPositions} open · {compactStats.exposurePct.toFixed(1)}% exposure
            </p>
            <p className="text-[11px] text-slate-400">Buying power {portfolio?.available_buying_power?.toFixed(0) ?? "0"}</p>
          </div>

          <div className="min-w-[220px] rounded-lg border border-terminal-line bg-black/25 p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Safety and Control</p>
            <p className={`mt-1 text-sm font-semibold ${control?.trading_enabled ? "text-green-400" : "text-red-400"}`}>
              {control?.trading_enabled ? "Trading Enabled" : "Kill Switch Active"}
            </p>
            <p className="text-[11px] text-slate-400">
              DD {compactStats.drawdownPct.toFixed(2)}% · Loss budget left {compactStats.riskBudgetLeft.toFixed(0)}
            </p>
          </div>

          <div className="min-w-[220px] rounded-lg border border-terminal-line bg-black/25 p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Goal Dashboard</p>
            <p className="mt-1 text-sm font-semibold text-amber-300">
              {compactStats.stress} stress · {compactStats.goalProb.toFixed(1)}% success
            </p>
            <p className="text-[11px] text-slate-400">Pressure {goal?.goal_pressure_multiplier?.toFixed(2) ?? "1.00"}x</p>
          </div>

          <div className="min-w-[220px] rounded-lg border border-terminal-line bg-black/25 p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">News and Context</p>
            <p className="mt-1 text-sm font-semibold text-blue-300">
              News {compactStats.newsStrength.toFixed(2)} · Ctx {compactStats.contextConfidence.toFixed(2)}x
            </p>
            <p className="text-[11px] text-slate-400">Focus {focusSymbol}</p>
          </div>

          <div className="min-w-[220px] rounded-lg border border-terminal-line bg-black/25 p-3">
            <p className="text-[10px] uppercase tracking-wider text-slate-500">Decision Audit</p>
            <p className="mt-1 text-sm font-semibold text-violet-300">
              {compactStats.accepted}/{compactStats.audits} accepted
            </p>
            <p className="text-[11px] text-slate-400">Latest {selectedAuditId?.slice(0, 8) ?? "none"}</p>
          </div>
        </div>
      </section>

      <section className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Coverage</div>
          <div className="mt-2 text-2xl font-semibold text-terminal-accent">{scan?.total_scanned ?? 0}</div>
          <div className="text-xs text-slate-400">Tickers scanned per cycle</div>
        </div>
        <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Execution Ready</div>
          <div className="mt-2 text-2xl font-semibold text-green-400">
            {(scan?.candidates ?? []).filter((c) => c.action_label === "EXECUTE").length}
          </div>
          <div className="text-xs text-slate-400">Candidates cleared for run</div>
        </div>
        <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Auto Mode</div>
          <div className={`mt-2 text-2xl font-semibold ${status?.auto_mode ? "text-green-400" : "text-slate-300"}`}>
            {status?.auto_mode ? "ON" : "OFF"}
          </div>
          <div className="text-xs text-slate-400">Interval: {status?.auto_interval_seconds ?? 300}s</div>
        </div>
      </section>

      <section className="mb-4 rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
        <h2 className="mb-2 text-sm font-semibold text-terminal-accent">Strategy Distribution</h2>
        <div className="grid grid-cols-2 gap-2 text-xs md:grid-cols-6">
          <div className="rounded border border-terminal-line px-2 py-2">OPTIONS: {strategyCounts.OPTIONS_PLAY}</div>
          <div className="rounded border border-terminal-line px-2 py-2">SWING: {strategyCounts.SWING_TRADE}</div>
          <div className="rounded border border-terminal-line px-2 py-2">DAY: {strategyCounts.DAY_TRADE}</div>
          <div className="rounded border border-terminal-line px-2 py-2">SCALP: {strategyCounts.SCALP}</div>
          <div className="rounded border border-terminal-line px-2 py-2">WATCH: {strategyCounts.WATCH}</div>
          <div className="rounded border border-terminal-line px-2 py-2">IGNORE: {strategyCounts.IGNORE}</div>
        </div>
      </section>

      <OrchestratorPanel
        scan={scan}
        status={status}
        loading={loading}
        onScan={handleScan}
        onToggleAutoMode={handleToggleAuto}
        onRunSymbol={handleOrchestratorRunSymbol}
      />

      <section className="mb-4 rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-terminal-accent">Operational Focus Symbol</h2>
          <Link
            href={`/terminal?symbol=${encodeURIComponent(focusSymbol)}`}
            className="rounded border border-terminal-line px-3 py-1.5 text-xs text-slate-300 hover:border-terminal-accent/60 hover:text-terminal-accent"
          >
            Drill Into Deep Terminal ({focusSymbol})
          </Link>
        </div>
        <div className="flex flex-wrap gap-2">
          {(topSymbols.length > 0 ? topSymbols : [focusSymbol]).map((sym) => (
            <button
              key={sym}
              onClick={() => setFocusSymbol(sym)}
              className={`rounded border px-3 py-1 text-xs transition ${
                focusSymbol === sym
                  ? "border-terminal-accent bg-terminal-accent/15 text-terminal-accent"
                  : "border-terminal-line bg-black/20 text-slate-300 hover:border-terminal-accent/50"
              }`}
            >
              {sym}
            </button>
          ))}
        </div>
      </section>

      <section className="grid grid-cols-1 gap-4 xl:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <PortfolioPanel portfolio={portfolio} />
          <GoalPanel goal={goal} onSetGoal={handleSetGoal} />
          <DecisionAuditPanel
            entries={decisionAudit}
            selectedAuditId={selectedAuditId}
            onSelect={handleSelectAudit}
          />
          <DecisionReplayPanel replay={decisionReplay} />
        </div>

        <aside className="space-y-4">
          <NewsPanel signal={newsSignal} audit={newsAudit} />
          <ContextPanel context={contextSignal} />
          <ControlPanel
            control={control}
            executionMode={executionMode}
            onToggleKillSwitch={handleToggleKillSwitch}
            onToggleAutonomous={handleToggleAutonomous}
            onRunAutonomousOnce={handleRunAutonomousOnce}
            onSetExecutionMode={handleSetExecutionMode}
          />
        </aside>
      </section>
    </main>
  );
}
