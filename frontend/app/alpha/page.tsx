"use client";

import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";

import ControlPanel from "../../components/ControlPanel";
import ContextPanel from "../../components/ContextPanel";
import DecisionAuditPanel from "../../components/DecisionAuditPanel";
import DecisionReplayPanel from "../../components/DecisionReplayPanel";
import GoalPanel from "../../components/GoalPanel";
import OrchestratorPanel, {
  type OrchestratorScan,
  type OrchestratorStatus,
} from "../../components/OrchestratorPanel";
import PortfolioPanel from "../../components/PortfolioPanel";
import AlphaHeader from "../../components/alpha/AlphaHeader";
import AlphaOpsTabs, { type AlphaOpsTab } from "../../components/alpha/AlphaOpsTabs";
import BrokerPolicyPanel from "../../components/alpha/BrokerPolicyPanel";
import BrokerRail from "../../components/alpha/BrokerRail";
import NewsFeedSettingsPanel from "../../components/alpha/NewsFeedSettingsPanel";
import DiscordSignalPanel, { type DiscordSignalStatus } from "../../components/alpha/DiscordSignalPanel";
import BrokerStatusMiniCard from "../../components/alpha/BrokerStatusMiniCard";
import RuntimeSummaryStrip from "../../components/alpha/RuntimeSummaryStrip";
import { apiFetch } from "../../lib/apiClient";
import { ensureHighTrust } from "../../lib/highTrust";

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
  current_price?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
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
  broker_accounts?: {
    broker: string;
    account_label: string;
    account_mode: string;
    connected: boolean;
    account_balance: number | null;
    buying_power: number | null;
    currency: string;
    last_error: string | null;
  }[];
  data_source?: string;
  degraded?: boolean;
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
  daily_loss_limit_pct?: number;
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
  options_sprint: {
    enabled: boolean;
    profile: string;
    target_amount: number | null;
    timeframe_days: number | null;
    objective_summary: string | null;
    activation_source: string;
    acknowledged_high_risk: boolean;
    allow_live_execution: boolean;
    live_execution_ready: boolean;
    live_execution_blockers: string[];
    recommended_execution_mode: "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING";
    strategy_bias: Record<string, number>;
    updated_at: string | null;
  };
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

const SYNTHETIC_AUDIT_PREFIX = "fallback-audit-";

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

type BrokerConnectionEntry = {
  provider: string;
  label: string;
  connected: boolean;
  configured?: boolean;
  planned?: boolean;
  connectable: boolean;
  disconnect_supported: boolean;
  auth_type: "oauth" | "api_key" | "unavailable" | "planned";
  permissions: string;
  mode: string | null;
  status_label: string;
  connect_path: string | null;
  disconnect_path: string | null;
  oauth_url?: string | null;
  updated_at: string | null;
  last_error: string | null;
  notes: string | null;
  capabilities: Record<string, boolean>;
};

type BrokerConnectionsResponse = {
  brokers: BrokerConnectionEntry[];
};

type BrokerPolicySummary = {
  policy: {
    equity_live: string;
    equity_live_weights: Record<string, number>;
    option_live_weights: Record<string, number>;
    crypto_live_weights: Record<string, number>;
  };
  brokers: Record<
    string,
    {
      execution_ready?: boolean;
      configured?: boolean;
      strengths?: string[];
      preferred_for?: string[];
      constraint?: string;
    }
  >;
  strategy_routing: Record<
    string,
    {
      active_candidates?: string[];
      selection_method?: string;
      constraint?: string;
    }
  >;
};

type NewsFeedSettingsResponse = {
  sources: Array<{
    source: string;
    url: string;
    enabled: boolean;
    weight: number;
  }>;
  refresh_seconds: number;
  updated_at: string | null;
};

type LightweightMetricsResponse = {
  window_days: number;
  scans_run: number;
  trades_triggered: number;
  top_strategies: Array<{ strategy: string; count: number }>;
};

type RuntimeReadinessResponse = {
  as_of: string;
  broker_connected: boolean;
  execution_mode: "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING";
  trading_enabled: boolean;
  autonomous_enabled: boolean;
  autonomous_cycles_run: number;
  latest_scan_candidates: number;
  latest_scan_age_seconds: number | null;
  open_positions: number;
  submitted_executions_24h: number;
  rejected_executions_24h: number;
  decision_audits_24h: number;
  news_audits_24h: number;
  coinbase_ws_connected: boolean;
  coinbase_ws_last_message_at: string | null;
  coinbase_ws_error: string | null;
  lightweight_7d: LightweightMetricsResponse;
};

type OpsSummaryResponse = {
  generated_at: string;
  window: {
    last_24h_start: string;
    last_7d_start: string;
  };
  growth: {
    users_total: number;
    users_created_7d: number;
  };
  funnel: {
    registered_users: number;
    twofa_verified_users: number;
    users_with_connected_broker: number;
    symbols_with_submitted_execution_24h: number;
  };
  conversions: {
    signup_to_twofa_verified_pct: number;
    twofa_verified_to_broker_connected_pct: number;
  };
  reliability: {
    active_sessions_24h: number;
    auth_failures_24h: number;
    executions_total_24h: number;
    executions_submitted_24h: number;
    execution_errors_24h: number;
    execution_submit_rate_pct: number;
    execution_error_rate_pct: number;
  };
};

type TruthDashboardResponse = {
  window_days: number;
  as_of: string;
  trades: number;
  settled_trades: number;
  win_rate: number;
  net_pnl: number;
  best_strategy: { strategy: string; trades: number; win_rate: number; net_pnl: number } | null;
  worst_strategy: { strategy: string; trades: number; win_rate: number; net_pnl: number } | null;
};

type MissionIntelligenceResponse = {
  operator_alerts?: Array<{
    code: string;
    phase: "WATCH" | "EARLY_WARNING" | "PREVENTIVE_SHIFT";
    severity: "INFO" | "WARNING" | "CRITICAL";
    title: string;
    message: string;
    score: number;
    target_mode?: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL";
    signals?: string[];
  }>;
  mission: {
    mission_style: string;
    risk_posture?: {
      mode: string;
      forced_style: string | null;
      reason: string;
    };
    goal_pressure_multiplier: number;
    stress_level: string;
    drawdown_pct: number;
    tuning: {
      concurrency_target: number;
      per_trade_cap_pct: number;
      min_confidence_floor: number;
      crypto_bias: number;
      allow_high_risk_sprint: boolean;
      sprint_active: boolean;
    };
    capital_buckets: Record<string, number>;
  };
  system_confidence?: {
    score: number;
    label: "LOW" | "MEDIUM" | "HIGH";
    factors: {
      data_sufficiency: number;
      strategy_diversity: number;
      win_rate_stability: number;
      drawdown_pressure: number;
    };
  };
  time_weighted_confidence?: {
    short_term_7d: { score: number; win_rate: number; sample_size: number };
    mid_term_30d: { score: number; win_rate: number; sample_size: number };
    long_term_90d: { score: number; win_rate: number; sample_size: number };
    blended_score: number;
  };
  strategy_evolution?: {
    mutations: Array<{ strategy: string; reason: string }>;
    clones: Array<{ strategy: string; clone_name: string; reason: string }>;
    suggested_experiments: number;
  };
  sprint_governance: {
    active: boolean;
    manual_override: boolean;
    auto_enabled: boolean;
    trigger_pressure: number;
    current_pressure: number;
    admitted_symbols: string[];
    extra_risk_budget_pct: number;
    deactivation_condition: string;
  };
  execution_quality: {
    sample_size: number;
    top_symbols: Array<{ symbol: string; quality_score: number }>;
    bottom_symbols: Array<{ symbol: string; quality_score: number }>;
    asset_class_quality: Record<string, { quality_score: number }>;
    regime_quality: Record<string, { quality_score: number }>;
    strategy_quality?: Record<string, { quality_score: number; win_rate: number; settled: number }>;
    bucket_quality?: Record<string, { quality_score: number; strategies: number }>;
    disabled_strategies?: string[];
    probation_strategies?: string[];
    strategy_kill_switches?: Array<{ strategy: string; window_trades: number; win_rate: number; threshold: number; disabled: boolean }>;
  };
  live_experiment_mode?: {
    variant: string;
    source: string;
    promoted_at: string | null;
    enable_evolution: boolean;
    enable_compounding: boolean;
  };
  meta_risk_governor?: {
    mode: string;
    global_exposure_multiplier: number;
    cooldown_active?: boolean;
    cooldown_until?: string | null;
    transitions_last_24h?: number;
    confidence_collapse?: { collapse: boolean; recent_avg_confidence: number };
    correlation_spike?: { spike: boolean; recent_avg_correlation: number };
  };
  system_mode?: {
    mode: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL";
    candidate_mode?: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL";
    reason: string;
    candidate_reason?: string;
    experiment_instability?: { score: number };
    system_health?: {
      score: number;
      label: "GREEN" | "YELLOW" | "RED";
      components?: {
        persistence_penalty: number;
        retry_penalty: number;
        backoff_penalty: number;
        conflict_penalty: number;
        drift_penalty: number;
        instability_penalty: number;
      };
    };
    predictive_prevention?: {
      early_warning: boolean;
      watch_active?: boolean;
      phase?: "CLEAR" | "WATCH" | "EARLY_WARNING" | "PREVENTIVE_SHIFT";
      warning_score: number;
      signals: string[];
      health_delta: number;
      trend_drop: number;
      preventive_mode?: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL" | null;
      preventive_shift_weight?: number;
      preventive_shift_applied?: boolean;
      base_mode?: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL";
      effective_mode?: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL";
      tuning?: {
        warning_threshold: number;
        watch_threshold: number;
        average_reliability: number;
        bias_aggressiveness: number;
        samples: number;
        weights: Record<string, number>;
        signal_quality?: Record<
          string,
          {
            precision: number;
            false_positive_rate: number;
            avg_lead_hours: number;
            lead_quality: number;
            support: number;
            contribution_multiplier: number;
            suppressed: boolean;
          }
        >;
        signal_rankings?: Array<{
          signal: string;
          weight: number;
          precision: number;
          lead_quality: number;
          false_positive_rate: number;
          suppressed: boolean;
        }>;
        event_precision: number;
        false_positive_rate: number;
        average_lead_hours?: number;
      };
    };
    mode_confidence?: {
      score: number;
      decayed_score?: number;
      decay_factor?: number;
      elapsed_minutes?: number;
      time_source?: string;
      drift_detected?: boolean;
      drift_magnitude_seconds?: number;
      drift_severity?: string;
      drift_confidence_reset_applied?: boolean;
      drift_confidence_reset_multiplier?: number;
      label: "HIGH" | "MEDIUM" | "LOW";
      risk_pressure_score: number;
      growth_pressure_score: number;
      components?: {
        drawdown_signal: number;
        confidence_signal: number;
        thrash_signal: number;
        correlation_signal: number;
      };
    };
    hysteresis?: {
      confirmed_mode: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL";
      pending_mode?: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL" | null;
      candidate_mode: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL";
      confirmation_required: number;
      confirmation_count: number;
      window_minutes?: number;
      progress: number;
      active: boolean;
      evaluation_bucket?: string | null;
      write_verification_ok?: boolean;
      write_verification_error?: string | null;
      write_retry_count?: number;
      write_backoff_seconds?: number;
    };
    blend?: {
      active: boolean;
      from_mode: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL";
      to_mode: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL";
      from_weight: number;
      to_weight: number;
    };
    assurance?: {
      forced_survival?: boolean;
      reason?: string | null;
      persistence_backoff_seconds?: number;
      drift_confidence_reset_applied?: boolean;
      drift_confidence_reset_multiplier?: number;
        recovery_hooks?: {
          db_reconnect_attempted: boolean;
          db_reconnect_success: boolean;
          state_rebuild_applied: boolean;
          rehydration_target_mode?: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL" | null;
        };
        recovery_phase?: {
          active: boolean;
          cycles_remaining: number;
          relearning_factor: number;
          rehydration_target_mode?: "AGGRESSIVE_GROWTH" | "BALANCED" | "DEFENSIVE" | "SURVIVAL" | null;
        };
      cross_signal_conflict?: {
        detected: boolean;
        score: number;
        confidence_multiplier: number;
        reasons: string[];
      };
    };
    controls?: {
      allocation_multiplier: number;
      trade_frequency_multiplier: number;
      min_confidence_floor: number;
      risk_tolerance: string;
      allow_evolution: boolean;
      allow_compounding: boolean;
    };
  };
  parity_watchdog: {
    status: "GREEN" | "YELLOW" | "RED";
    mode: string;
    issues: string[];
  };
};

type MissionScenarioResponse = {
  current_capital: number;
  target_capital: number;
  timeframe_days: number;
  required_total_return: number;
  required_daily_return: number;
  implied_goal_pressure: number;
  recommended_mission_style: string;
  target_unrealistic: boolean;
  refuse_activation: boolean;
  message: string;
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

type StrategyKillSwitchOverridesResponse = {
  manual_force_enabled: string[];
};

const VALID_STRATEGY_OVERRIDE_VALUES = new Set([
  "OPTIONS_PLAY",
  "SWING_TRADE",
  "DAY_TRADE",
  "SCALP",
  "WATCH",
  "IGNORE",
]);

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
  const [decisionAudit, setDecisionAudit] = useState<DecisionAuditSummary[] | null>(null);
  const [selectedAuditId, setSelectedAuditId] = useState<string | null>(null);
  const [decisionReplay, setDecisionReplay] = useState<DecisionReplayResponse | null>(null);
  const [oauthStatus, setOauthStatus] = useState<"idle" | "connected" | "error">("idle");
  const [oauthReason, setOauthReason] = useState<string>("");
  const [brokerConnections, setBrokerConnections] = useState<BrokerConnectionEntry[]>([]);
  const [brokerPolicy, setBrokerPolicy] = useState<BrokerPolicySummary | null>(null);
  const [newsFeedSettings, setNewsFeedSettings] = useState<NewsFeedSettingsResponse | null>(null);
  const [discordSignalStatus, setDiscordSignalStatus] = useState<DiscordSignalStatus | null>(null);
  const [discordWatchlist, setDiscordWatchlist] = useState<Array<{ symbol: string; asset_class: string; source: string; note: string | null; pinned_by: string | null; pinned_at: string }>>([]);
  const [selectedBrokerProvider, setSelectedBrokerProvider] = useState<string | null>(null);
  const [brokerDetailsProvider, setBrokerDetailsProvider] = useState<string | null>(null);
  const [connectingProvider, setConnectingProvider] = useState<string | null>(null);
  const [disconnectingProvider, setDisconnectingProvider] = useState<string | null>(null);
  const [alphaOpsTab, setAlphaOpsTab] = useState<AlphaOpsTab>("portfolio");
  const [launchMetrics, setLaunchMetrics] = useState<LightweightMetricsResponse | null>(null);
  const [runtimeReadiness, setRuntimeReadiness] = useState<RuntimeReadinessResponse | null>(null);
  const [opsSummary, setOpsSummary] = useState<OpsSummaryResponse | null>(null);
  const [truthDashboard, setTruthDashboard] = useState<TruthDashboardResponse | null>(null);
  const [missionIntel, setMissionIntel] = useState<MissionIntelligenceResponse | null>(null);
  const [manualForceEnabledStrategies, setManualForceEnabledStrategies] = useState<string[]>([]);
  const [overrideStrategyInput, setOverrideStrategyInput] = useState<string>("");
  const [overrideBusyStrategy, setOverrideBusyStrategy] = useState<string | null>(null);
  const [pendingClearOverrideStrategy, setPendingClearOverrideStrategy] = useState<string | null>(null);
  const [scenarioTarget, setScenarioTarget] = useState<number>(205000);
  const [scenarioDays, setScenarioDays] = useState<number>(3);
  const [missionScenario, setMissionScenario] = useState<MissionScenarioResponse | null>(null);
  const [runtimeToasts, setRuntimeToasts] = useState<RuntimeToast[]>([]);
  const brokerModalCloseButtonRef = useRef<HTMLButtonElement | null>(null);
  const clearOverrideCancelButtonRef = useRef<HTMLButtonElement | null>(null);
  const seenExecutionIdsRef = useRef<Set<string>>(new Set());
  const executionBaselineReadyRef = useRef(false);
  const autonomousCycleBaselineRef = useRef<number | null>(null);
  const killSwitchDisabledBaselineRef = useRef<Set<string> | null>(null);
  const predictiveAlertBaselineRef = useRef<Set<string> | null>(null);

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

    if (oauth === "connected" || oauth === "error") {
      qs.delete("alpaca_oauth");
      qs.delete("reason");
      const nextSearch = qs.toString();
      const nextUrl = `${window.location.pathname}${nextSearch ? `?${nextSearch}` : ""}${window.location.hash}`;
      window.history.replaceState({}, "", nextUrl);
    }
  }, []);

  useEffect(() => {
    if (!brokerDetailsProvider) {
      return;
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setBrokerDetailsProvider(null);
      }
    };

    window.addEventListener("keydown", handleEscape);
    brokerModalCloseButtonRef.current?.focus();

    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, [brokerDetailsProvider]);

  useEffect(() => {
    if (!pendingClearOverrideStrategy) {
      return;
    }

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setPendingClearOverrideStrategy(null);
      }
    };

    window.addEventListener("keydown", handleEscape);
    clearOverrideCancelButtonRef.current?.focus();

    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, [pendingClearOverrideStrategy]);

  async function refreshBrokerConnections() {
    const [brokerRes, policyRes] = await Promise.all([
      fetch(`${API_BASE}/agents/brokers/connections`),
      fetch(`${API_BASE}/agents/brokers/policy`),
    ]);
    const brokerData = await parseJsonOrNull<BrokerConnectionsResponse>(brokerRes);
    const policyData = await parseJsonOrNull<BrokerPolicySummary>(policyRes);
    setBrokerConnections(brokerData?.brokers ?? []);
    setBrokerPolicy(policyData);
  }

  async function refreshLaunchMetrics() {
    const metricsRes = await fetch(`${API_BASE}/metrics/lightweight?days=7`);
    const metricsData = await parseJsonOrNull<LightweightMetricsResponse>(metricsRes);
    setLaunchMetrics(metricsData);
  }

  async function refreshRuntimeReadiness() {
    const [readinessRes, missionRes, truthRes, overrideRes] = await Promise.all([
      fetch(`${API_BASE}/metrics/runtime-readiness`),
      fetch(`${API_BASE}/metrics/mission-intelligence`),
      fetch(`${API_BASE}/metrics/truth-dashboard?days=7`),
      fetch(`${API_BASE}/control/strategy-kill-switch`),
    ]);
    const readiness = await parseJsonOrNull<RuntimeReadinessResponse>(readinessRes);
    const missionData = await parseJsonOrNull<MissionIntelligenceResponse>(missionRes);
    const truthData = await parseJsonOrNull<TruthDashboardResponse>(truthRes);
    const overrideData = await parseJsonOrNull<StrategyKillSwitchOverridesResponse>(overrideRes);
    setRuntimeReadiness(readiness);
    setMissionIntel(missionData);
    setTruthDashboard(truthData);
    setManualForceEnabledStrategies(overrideData?.manual_force_enabled ?? []);
  }

  async function refreshOpsSummary() {
    const res = await fetch(`${API_BASE}/telemetry/ops-summary`);
    const data = await parseJsonOrNull<OpsSummaryResponse>(res);
    setOpsSummary(data);
  }

  async function setStrategyKillSwitchOverride(strategy: string, forceEnabled: boolean) {
    const normalized = strategy.trim().toUpperCase();
    if (!normalized) {
      pushRuntimeToast("Enter a strategy to override.", "warning");
      return;
    }
    if (!VALID_STRATEGY_OVERRIDE_VALUES.has(normalized)) {
      pushRuntimeToast(
        "Invalid strategy override. Use OPTIONS_PLAY, SWING_TRADE, DAY_TRADE, SCALP, WATCH, or IGNORE. High-risk is not a strategy override value.",
        "warning",
      );
      return;
    }

    setOverrideBusyStrategy(normalized);
    try {
      const params = new URLSearchParams({ strategy: normalized });
      if (forceEnabled) {
        params.set("force_enabled", "true");
      }
      const endpoint = `${API_BASE}/control/strategy-kill-switch/override?${params.toString()}`;
      const res = await fetch(endpoint, {
        method: forceEnabled ? "POST" : "DELETE",
      });
      const data = await parseJsonOrNull<StrategyKillSwitchOverridesResponse>(res);
      if (!res.ok || !data) {
        pushRuntimeToast(`Failed to ${forceEnabled ? "set" : "clear"} override for ${normalized}.`, "error");
        return;
      }
      setManualForceEnabledStrategies(data.manual_force_enabled ?? []);
      setOverrideStrategyInput("");
      pushRuntimeToast(
        forceEnabled
          ? `Manual override enabled for ${normalized}.`
          : `Manual override cleared for ${normalized}.`,
        forceEnabled ? "success" : "warning"
      );
      await refreshRuntimeReadiness();
    } finally {
      setOverrideBusyStrategy(null);
    }
  }

  async function confirmClearStrategyOverride() {
    if (!pendingClearOverrideStrategy) {
      return;
    }
    const strategy = pendingClearOverrideStrategy;
    setPendingClearOverrideStrategy(null);
    await setStrategyKillSwitchOverride(strategy, false);
  }

  async function runMissionScenario(targetCapital = scenarioTarget, timeframeDays = scenarioDays) {
    const params = new URLSearchParams({
      target_capital: String(targetCapital),
      timeframe_days: String(timeframeDays),
    });
    const simRes = await fetch(`${API_BASE}/control/mission/simulate?${params.toString()}`);
    const simData = await parseJsonOrNull<MissionScenarioResponse>(simRes);
    setMissionScenario(simData);
  }

  function pushRuntimeToast(message: string, tone: RuntimeToast["tone"]) {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    setRuntimeToasts((current) => [...current.slice(-2), { id, tone, message }]);
    window.setTimeout(() => {
      setRuntimeToasts((current) => current.filter((toast) => toast.id !== id));
    }, 6000);
  }

  useEffect(() => {
    const disabled = new Set(missionIntel?.execution_quality.disabled_strategies ?? []);
    const baseline = killSwitchDisabledBaselineRef.current;
    if (baseline === null) {
      killSwitchDisabledBaselineRef.current = disabled;
      return;
    }

    for (const strategy of disabled) {
      if (!baseline.has(strategy)) {
        pushRuntimeToast(`Strategy kill switch activated: ${strategy}`, "warning");
      }
    }
    for (const strategy of baseline) {
      if (!disabled.has(strategy)) {
        pushRuntimeToast(`Strategy kill switch cleared: ${strategy}`, "success");
      }
    }

    killSwitchDisabledBaselineRef.current = disabled;
  }, [missionIntel]);

  useEffect(() => {
    const alerts = missionIntel?.operator_alerts ?? [];
    const signatures = new Set(alerts.map((alert) => `${alert.code}:${alert.phase}:${alert.target_mode ?? "UNKNOWN"}`));
    const baseline = predictiveAlertBaselineRef.current;
    if (baseline === null) {
      predictiveAlertBaselineRef.current = signatures;
      return;
    }

    for (const alert of alerts) {
      const signature = `${alert.code}:${alert.phase}:${alert.target_mode ?? "UNKNOWN"}`;
      if (baseline.has(signature)) {
        continue;
      }
      pushRuntimeToast(
        `${alert.title}: ${alert.message}`,
        alert.severity === "CRITICAL" ? "error" : "warning"
      );
    }

    predictiveAlertBaselineRef.current = signatures;
  }, [missionIntel]);

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
      const scanRes = await apiFetch(`${API_BASE}/orchestrator/scan?limit=12`, {
        apiBase: API_BASE,
        method: "POST",
      });
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
    const [portfolioRes, controlRes, executionModeRes, goalRes, historyRes, missionRes] = await Promise.all([
      fetch(`${API_BASE}/portfolio`),
      fetch(`${API_BASE}/control`),
      fetch(`${API_BASE}/agents/execution-mode`),
      fetch(`${API_BASE}/agents/goal/status`),
      fetch(`${API_BASE}/agents/execution-history?limit=10`),
      fetch(`${API_BASE}/metrics/mission-intelligence`),
    ]);

    const portfolioData = await parseJsonOrNull<PortfolioResponse>(portfolioRes);
    const controlData = await parseJsonOrNull<ControlResponse>(controlRes);
    const executionModeData = await parseJsonOrNull<ExecutionModeResponse>(executionModeRes);
    const goalData = await parseJsonOrNull<GoalStatusResponse>(goalRes);
    const historyData = await parseJsonOrNull<ExecutionHistoryResponse>(historyRes);
    const missionData = await parseJsonOrNull<MissionIntelligenceResponse>(missionRes);

    setPortfolio(portfolioData);
    setControl(controlData);
    setExecutionMode(executionModeData?.mode ?? null);
    setGoal(goalData);
    setMissionIntel(missionData);

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

  async function refreshNewsFeedSettings() {
    const response = await fetch(`${API_BASE}/control/news-feeds`);
    const data = await parseJsonOrNull<NewsFeedSettingsResponse>(response);
    setNewsFeedSettings(data);
  }

  async function refreshDiscordSignals() {
    const [statusRes, watchRes] = await Promise.all([
      fetch(`${API_BASE}/discord/signals/status`),
      fetch(`${API_BASE}/discord/signals/watchlist`),
    ]);
    const statusData = await parseJsonOrNull<DiscordSignalStatus>(statusRes);
    const watchData = await parseJsonOrNull<{ entries: typeof discordWatchlist }>(watchRes);
    setDiscordSignalStatus(statusData);
    setDiscordWatchlist(watchData?.entries ?? []);
  }

  async function handlePinDiscordSymbol(symbol: string, assetClass: string, note: string) {
    const ok = await ensureHighTrustOrNotify();
    if (!ok) { pushRuntimeToast("Security verification was cancelled.", "warning"); return; }
    await apiFetch(`${API_BASE}/discord/signals/watchlist/${symbol}`, {
      apiBase: API_BASE,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ asset_class: assetClass, note: note || null }),
    });
    await refreshDiscordSignals();
    pushRuntimeToast(`${symbol} pinned to Discord signal watchlist.`, "success");
  }

  async function handleUnpinDiscordSymbol(symbol: string) {
    const ok = await ensureHighTrustOrNotify();
    if (!ok) { pushRuntimeToast("Security verification was cancelled.", "warning"); return; }
    await apiFetch(`${API_BASE}/discord/signals/watchlist/${symbol}`, {
      apiBase: API_BASE,
      method: "DELETE",
    });
    await refreshDiscordSignals();
    pushRuntimeToast(`${symbol} removed from Discord signal watchlist.`, "success");
  }

  async function refreshSymbolIntel(currentFocusSymbol: string, preferredAuditId: string | null = selectedAuditId) {
    const [contextRes, newsRes, auditRes] = await Promise.all([
      fetch(`${API_BASE}/agents/context/${currentFocusSymbol}`),
      fetch(`${API_BASE}/agents/news/${currentFocusSymbol}`),
      fetch(`${API_BASE}/agents/audit/decisions?limit=25`),
    ]);

    const contextData = await parseJsonOrNull<ContextSignalResponse>(contextRes);
    const newsData = await parseJsonOrNull<NewsSignalResponse>(newsRes);
    const auditData = await parseJsonOrNull<DecisionAuditSummaryListResponse>(auditRes);

    setContextSignal(contextData);
    setNewsSignal(newsData);

    const liveAudits = auditData?.entries ?? [];
    const fallbackAudits: DecisionAuditSummary[] =
      liveAudits.length === 0
        ? (control?.rejected_trades ?? []).slice(-8).map((item, index) => ({
            audit_id: `${SYNTHETIC_AUDIT_PREFIX}${index}-${item.symbol}-${item.timestamp}`,
            timestamp: item.timestamp,
            decision_type: "SWARM",
            symbol: item.symbol,
            status: "REJECTED",
            cycle_id: null,
          }))
        : [];

    const audits = liveAudits.length > 0 ? liveAudits : fallbackAudits;
    setDecisionAudit(audits);
    const nextAuditId = preferredAuditId && audits.some((entry) => entry.audit_id === preferredAuditId)
      ? preferredAuditId
      : (audits[0]?.audit_id ?? null);
    setSelectedAuditId(nextAuditId);

    if (!nextAuditId) {
      setDecisionReplay(null);
      return;
    }

    if (nextAuditId.startsWith(SYNTHETIC_AUDIT_PREFIX)) {
      const synthetic = audits.find((item) => item.audit_id === nextAuditId);
      if (!synthetic) {
        setDecisionReplay(null);
        return;
      }
      setDecisionReplay({
        audit_id: synthetic.audit_id,
        symbol: synthetic.symbol,
        decision_type: synthetic.decision_type,
        status: synthetic.status,
        generated_at: synthetic.timestamp,
        replay_steps: [
          {
            stage: "SUMMARY",
            title: "Fallback Summary",
            summary: "Derived from control-panel rejections while persisted audit payload is unavailable.",
            payload: {
              source: "control.rejected_trades",
              symbol: synthetic.symbol,
            },
          },
        ],
        why_not: ["Decision audit payload unavailable; showing rejection summary fallback."],
      });
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
      await runMissionScenario();
    }

    boot().catch((err: unknown) => {
      console.error("Failed to load alpha dashboard", err);
    });

    refreshBrokerConnections().catch((err: unknown) => {
      console.error("Failed to fetch broker connection inventory", err);
    });

    refreshDiscordSignals().catch((err: unknown) => {
      void err;
    });
    refreshNewsFeedSettings().catch((err: unknown) => {
      console.error("Failed to fetch news feed settings", err);
    });

    refreshLaunchMetrics().catch((err: unknown) => {
      console.error("Failed to fetch lightweight metrics", err);
    });

    refreshRuntimeReadiness().catch((err: unknown) => {
      console.error("Failed to fetch runtime readiness telemetry", err);
    });

    refreshOpsSummary().catch((err: unknown) => {
      console.error("Failed to fetch launch ops summary", err);
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
        refreshBrokerConnections(),
        refreshRuntimeReadiness(),
        refreshOpsSummary(),
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

  async function ensureHighTrustOrNotify(): Promise<boolean> {
    try {
      return await ensureHighTrust({ apiBase: API_BASE });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Secure verification failed";
      if (message === "Authentication required") {
        window.location.href = "/login?next=/alpha";
        return false;
      }
      pushRuntimeToast(message, "error");
      return false;
    }
  }

  async function handleToggleAuto(enabled: boolean) {
    await apiFetch(`${API_BASE}/orchestrator/mode`, {
      apiBase: API_BASE,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auto_mode: enabled }),
    });
    const statusRes = await fetch(`${API_BASE}/orchestrator/status`);
    const statusData = await parseJsonOrNull<OrchestratorStatus>(statusRes);
    setStatus(statusData);
  }

  async function handleToggleKillSwitch(enabled: boolean) {
    const ok = await ensureHighTrustOrNotify();
    if (!ok) {
      pushRuntimeToast("Security verification was cancelled.", "warning");
      return;
    }
    await apiFetch(`${API_BASE}/control/kill-switch`, {
      apiBase: API_BASE,
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
    const ok = await ensureHighTrustOrNotify();
    if (!ok) {
      pushRuntimeToast("Security verification was cancelled.", "warning");
      return;
    }
    await apiFetch(`${API_BASE}/control/autonomous`, {
      apiBase: API_BASE,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ enabled }),
    });
    // Keep scan automation and autonomous execution aligned to avoid dual-mode confusion.
    await apiFetch(`${API_BASE}/orchestrator/mode`, {
      apiBase: API_BASE,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auto_mode: enabled }),
    });
    const orchestratorStatusRes = await fetch(`${API_BASE}/orchestrator/status`);
    const orchestratorStatusData = await parseJsonOrNull<OrchestratorStatus>(orchestratorStatusRes);
    setStatus(orchestratorStatusData);
    const controlRes = await fetch(`${API_BASE}/control`);
    const controlData = await parseJsonOrNull<ControlResponse>(controlRes);
    setControl(controlData);
    pushRuntimeToast(
      enabled
        ? "Autonomous execution enabled and scan auto mode turned on."
        : "Autonomous execution stopped and scan auto mode turned off.",
      enabled ? "success" : "warning",
    );
  }

  async function handleRunAutonomousOnce() {
    const ok = await ensureHighTrustOrNotify();
    if (!ok) {
      pushRuntimeToast("Security verification was cancelled.", "warning");
      return;
    }
    await apiFetch(`${API_BASE}/control/autonomous/run-once`, {
      apiBase: API_BASE,
      method: "POST",
    });
    await Promise.all([refreshRuntimeState(true), refreshScanState(false)]);
  }

  async function handleSetExecutionMode(mode: "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING") {
    const ok = await ensureHighTrustOrNotify();
    if (!ok) {
      pushRuntimeToast("Security verification was cancelled.", "warning");
      return;
    }
    await apiFetch(`${API_BASE}/agents/execution-mode`, {
      apiBase: API_BASE,
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
    await apiFetch(`${API_BASE}/agents/goal`, {
      apiBase: API_BASE,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const goalRes = await fetch(`${API_BASE}/agents/goal/status`);
    const goalData = await parseJsonOrNull<GoalStatusResponse>(goalRes);
    setGoal(goalData);
  }


  async function handleUpdateLimits(data: { daily_loss_limit_pct: number; max_drawdown_limit_pct: number }) {
    const ok = await ensureHighTrustOrNotify();
    if (!ok) {
      pushRuntimeToast("Security verification was cancelled.", "warning");
      return;
    }
    await apiFetch(`${API_BASE}/control/limits`, {
      apiBase: API_BASE,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    const controlRes = await fetch(`${API_BASE}/control`);
    const controlData = await parseJsonOrNull<ControlResponse>(controlRes);
    setControl(controlData);
    pushRuntimeToast("Risk limits updated.", "success");
  }

  async function handleSetOptionsSprint(enabled: boolean) {
    const ok = await ensureHighTrustOrNotify();
    if (!ok) {
      pushRuntimeToast("Security verification was cancelled.", "warning");
      return;
    }
    if (enabled) {
      await fetch(`${API_BASE}/control/options-sprint`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          enabled: true,
          activation_source: "manual_ui",
          acknowledged_high_risk: true,
          allow_live_execution: false,
          objective_summary: "Manual activation from control panel",
        }),
      });
    } else {
      await fetch(`${API_BASE}/control/options-sprint`, { method: "DELETE" });
    }
    const controlRes = await fetch(`${API_BASE}/control`);
    const controlData = await parseJsonOrNull<ControlResponse>(controlRes);
    setControl(controlData);
    pushRuntimeToast(enabled ? "Options sprint profile activated." : "Options sprint profile disabled.", enabled ? "warning" : "success");
  }

  async function handleSaveNewsFeedSettings(payload: { enabled_sources: string[]; source_weights: Record<string, number> }) {
    const ok = await ensureHighTrustOrNotify();
    if (!ok) {
      pushRuntimeToast("Security verification was cancelled.", "warning");
      return;
    }
    await apiFetch(`${API_BASE}/control/news-feeds`, {
      apiBase: API_BASE,
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    await refreshNewsFeedSettings();
    pushRuntimeToast("News feed settings updated.", "success");
  }

  async function handleSelectAudit(auditId: string) {
    setSelectedAuditId(auditId);

    if (auditId.startsWith(SYNTHETIC_AUDIT_PREFIX)) {
      const synthetic = decisionAudit?.find((entry) => entry.audit_id === auditId);
      if (!synthetic) {
        setDecisionReplay(null);
        return;
      }
      setDecisionReplay({
        audit_id: synthetic.audit_id,
        symbol: synthetic.symbol,
        decision_type: synthetic.decision_type,
        status: synthetic.status,
        generated_at: synthetic.timestamp,
        replay_steps: [
          {
            stage: "SUMMARY",
            title: "Fallback Summary",
            summary: "Derived from control-panel rejections while persisted audit payload is unavailable.",
            payload: {
              source: "control.rejected_trades",
              symbol: synthetic.symbol,
            },
          },
        ],
        why_not: ["Decision audit payload unavailable; showing rejection summary fallback."],
      });
      return;
    }

    const replayRes = await fetch(`${API_BASE}/agents/audit/replay/${auditId}`);
    const replayData = await parseJsonOrNull<DecisionReplayResponse>(replayRes);
    setDecisionReplay(replayData);
  }

  async function handleConnectBroker(provider: string, connectPath: string | null) {
    if (!connectPath) {
      return;
    }
    setConnectingProvider(provider);
    try {
      const ok = await ensureHighTrustOrNotify();
      if (!ok) {
        pushRuntimeToast("Security verification was cancelled.", "warning");
        return;
      }
      window.location.href = `${API_BASE}${connectPath}`;
    } finally {
      setConnectingProvider(null);
    }
  }

  async function handleDisconnectBroker(provider: string, disconnectPath: string | null) {
    if (!disconnectPath) {
      return;
    }
    setDisconnectingProvider(provider);
    try {
      const ok = await ensureHighTrustOrNotify();
      if (!ok) {
        pushRuntimeToast("Security verification was cancelled.", "warning");
        return;
      }
      await apiFetch(`${API_BASE}${disconnectPath}`, {
        apiBase: API_BASE,
        method: "POST",
      });
      if (provider === "alpaca") {
        setOauthStatus("idle");
        setOauthReason("");
      }
      await Promise.all([refreshBrokerConnections(), refreshLaunchMetrics(), refreshRuntimeState(false)]);
      pushRuntimeToast(`${provider[0]?.toUpperCase()}${provider.slice(1)} connection removed.`, "warning");
    } finally {
      setDisconnectingProvider(null);
    }
  }


  const connectedBrokerCount = brokerConnections.filter((broker) => broker.connected).length;
  const selectedBroker = useMemo(() => {
    if (!selectedBrokerProvider) {
      return null;
    }
    return brokerConnections.find((broker) => broker.provider === selectedBrokerProvider) ?? null;
  }, [selectedBrokerProvider, brokerConnections]);

  const activeBroker = useMemo(() => {
    if (!brokerDetailsProvider) {
      return null;
    }
    return brokerConnections.find((broker) => broker.provider === brokerDetailsProvider) ?? null;
  }, [brokerDetailsProvider, brokerConnections]);

  useEffect(() => {
    if (selectedBrokerProvider && !selectedBroker) {
      setSelectedBrokerProvider(null);
    }
  }, [selectedBroker, selectedBrokerProvider]);

  useEffect(() => {
    if (brokerDetailsProvider && !activeBroker) {
      setBrokerDetailsProvider(null);
    }
  }, [activeBroker, brokerDetailsProvider]);

  function handleOrchestratorRunSymbol(symbol: string) {
    setFocusSymbol(symbol);
  }

  const runtimePhase = useMemo(() => {
    if (!runtimeReadiness) {
      return { label: "Loading Runtime State", tone: "text-slate-300", panel: "border-terminal-line bg-black/20" };
    }
    if (!runtimeReadiness.broker_connected) {
      return { label: "Broker Not Connected", tone: "text-amber-300", panel: "border-amber-500/40 bg-amber-500/10" };
    }
    if (runtimeReadiness.execution_mode === "SIMULATION") {
      return { label: "Live Data, Simulation Execution", tone: "text-blue-300", panel: "border-blue-500/40 bg-blue-500/10" };
    }
    if (runtimeReadiness.execution_mode === "PAPER_TRADING" && runtimeReadiness.submitted_executions_24h === 0) {
      return { label: "Paper Trading Armed, No Executions Yet", tone: "text-amber-200", panel: "border-amber-500/40 bg-amber-500/10" };
    }
    if (runtimeReadiness.execution_mode === "PAPER_TRADING") {
      return { label: "Paper Trading Active", tone: "text-green-200", panel: "border-green-500/40 bg-green-500/10" };
    }
    return { label: "Live Capital Mode", tone: "text-green-100", panel: "border-green-500/40 bg-green-500/10" };
  }, [runtimeReadiness]);

  const opsAlertTone = useMemo(() => {
    if (!opsSummary) {
      return "text-slate-300";
    }
    if (opsSummary.reliability.execution_error_rate_pct >= 25 || opsSummary.reliability.auth_failures_24h >= 25) {
      return "text-red-300";
    }
    if (opsSummary.reliability.execution_error_rate_pct >= 10 || opsSummary.reliability.auth_failures_24h >= 10) {
      return "text-amber-300";
    }
    return "text-green-300";
  }, [opsSummary]);

  const terminalHref = useMemo(() => {
    const query = new URLSearchParams({ symbol: focusSymbol });
    if (selectedBrokerProvider) {
      query.set("broker", selectedBrokerProvider);
    }
    return `/terminal?${query.toString()}`;
  }, [focusSymbol, selectedBrokerProvider]);

  const scopedPortfolio = useMemo(() => {
    if (!portfolio || !selectedBrokerProvider) {
      return portfolio;
    }
    const brokerAccounts = (portfolio.broker_accounts ?? []).filter(
      (acct) => acct.broker.toLowerCase() === selectedBrokerProvider.toLowerCase(),
    );
    if (brokerAccounts.length === 0) {
      return portfolio;
    }
    return {
      ...portfolio,
      broker_accounts: brokerAccounts,
    };
  }, [portfolio, selectedBrokerProvider]);

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

      <AlphaHeader
        executionMode={executionMode}
        runtimePhase={{ label: runtimePhase.label, tone: runtimePhase.tone }}
        focusSymbol={focusSymbol}
        selectedBrokerLabel={selectedBroker?.label ?? null}
        terminalHref={terminalHref}
      />

      {oauthStatus !== "idle" && (
        <div
          className={`mb-4 rounded border px-3 py-2 text-xs ${
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

      <section className="grid grid-cols-1 gap-4 lg:grid-cols-[220px_minmax(0,1fr)_360px]">
        <aside className="space-y-3">
          <BrokerRail
            brokers={brokerConnections}
            selectedBrokerProvider={selectedBrokerProvider}
            onSelectBroker={setSelectedBrokerProvider}
            onOpenDetails={setBrokerDetailsProvider}
          />

          <BrokerPolicyPanel policy={brokerPolicy} selectedBrokerProvider={selectedBrokerProvider} />

          <NewsFeedSettingsPanel settings={newsFeedSettings} onSave={handleSaveNewsFeedSettings} />
          <DiscordSignalPanel
            status={discordSignalStatus}
            watchlist={discordWatchlist}
            onPin={handlePinDiscordSymbol}
            onUnpin={handleUnpinDiscordSymbol}
            onRefresh={refreshDiscordSignals}
          />

          {activeBroker && (
            <div className="rounded-xl border border-terminal-line bg-terminal-panel/70 p-3 text-xs">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="font-semibold text-terminal-accent">{activeBroker.label} Details</h3>
                <button
                  ref={brokerModalCloseButtonRef}
                  type="button"
                  onClick={() => setBrokerDetailsProvider(null)}
                  className="rounded border border-terminal-line px-2 py-1 text-[10px] text-slate-300"
                >
                  Close
                </button>
              </div>
              <div className="space-y-1 text-[11px] text-slate-300">
                <div>Status: {activeBroker.status_label}</div>
                <div>Permissions: {activeBroker.permissions}</div>
                <div>Auth: {activeBroker.auth_type.replace("_", " ")}</div>
                <div>Mode: {activeBroker.mode ?? "N/A"}</div>
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {activeBroker.connect_path && activeBroker.connectable && !activeBroker.connected && (
                  <button
                    type="button"
                    disabled={connectingProvider === activeBroker.provider}
                    onClick={() => void handleConnectBroker(activeBroker.provider, activeBroker.connect_path)}
                    className="rounded border border-terminal-accent bg-terminal-accent/10 px-2 py-1 text-[11px] text-terminal-accent"
                  >
                    {connectingProvider === activeBroker.provider ? "Securing..." : "Connect"}
                  </button>
                )}
                <button
                  type="button"
                  disabled={!activeBroker.connected || !activeBroker.disconnect_supported || disconnectingProvider === activeBroker.provider}
                  onClick={() => handleDisconnectBroker(activeBroker.provider, activeBroker.disconnect_path)}
                  className="rounded border border-red-500/40 bg-red-500/10 px-2 py-1 text-[11px] text-red-300 disabled:opacity-40"
                >
                  {disconnectingProvider === activeBroker.provider ? "Disconnecting..." : "Disconnect"}
                </button>
              </div>
              {activeBroker.last_error ? <div className="mt-2 text-[11px] text-red-300">Last error: {activeBroker.last_error}</div> : null}
            </div>
          )}

          {launchMetrics && (
            <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3 text-[11px] text-slate-300">
              Last {launchMetrics.window_days}d: {launchMetrics.scans_run} scans · {launchMetrics.trades_triggered} trades · top {launchMetrics.top_strategies[0]?.strategy ?? "N/A"}
            </div>
          )}
        </aside>

        <div className="space-y-4">
          <RuntimeSummaryStrip
            runtimePhaseLabel={runtimePhase.label}
            brokerConnectedCount={connectedBrokerCount}
            executionReadyCount={(scan?.candidates ?? []).filter((c) => c.action_label === "EXECUTE").length}
            automationOn={Boolean(status?.auto_mode || control?.autonomous_enabled)}
            scanAgeSeconds={runtimeReadiness?.latest_scan_age_seconds ?? null}
            selectedBrokerLabel={selectedBroker?.label ?? null}
          />

          <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h2 className="text-sm font-semibold text-terminal-accent">Discovery Workspace</h2>
                <p className="text-xs text-slate-400">
                  Ranked opportunities with operator actions in {selectedBroker?.label ?? "all-brokers"} context.
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => setFocusSymbol(scan?.candidates?.[0]?.symbol ?? focusSymbol)}
                  className="rounded border border-terminal-line px-2 py-1 text-[11px] text-slate-300"
                >
                  Set Focus
                </button>
                <Link
                  href={terminalHref}
                  className="rounded border border-terminal-line px-2 py-1 text-[11px] text-slate-300 hover:border-terminal-accent/60"
                >
                  Open in Deep Terminal
                </Link>
              </div>
            </div>

            <OrchestratorPanel
              scan={scan}
              status={status}
              loading={loading}
              onScan={handleScan}
              onToggleAutoMode={handleToggleAuto}
              onRunSymbol={handleOrchestratorRunSymbol}
            />
          </section>

          <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-sm font-semibold text-terminal-accent">
                {selectedBroker?.label ?? "All Brokers"} · Focus Symbol: {focusSymbol}
              </h2>
              <Link
                href={terminalHref}
                className="rounded border border-terminal-line px-3 py-1.5 text-xs text-slate-300 hover:border-terminal-accent/60 hover:text-terminal-accent"
              >
                Prepare in Terminal
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

          <AlphaOpsTabs
            activeTab={alphaOpsTab}
            onTabChange={setAlphaOpsTab}
            panels={{
              portfolio: <PortfolioPanel portfolio={scopedPortfolio} />,
              goal: <GoalPanel goal={goal} onSetGoal={handleSetGoal} />,
              audit: (
                <DecisionAuditPanel
                  entries={decisionAudit}
                  selectedAuditId={selectedAuditId}
                  onSelect={handleSelectAudit}
                />
              ),
              replay: <DecisionReplayPanel replay={decisionReplay} />,
            }}
          />

          <details className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
            <summary className="cursor-pointer text-sm font-semibold text-terminal-accent">Runtime and Governance Details</summary>
            <div className="mt-3 grid grid-cols-1 gap-3 text-xs md:grid-cols-2">
              <div className="rounded border border-terminal-line bg-black/20 p-3 text-slate-300">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Ops Pulse</div>
                <div className={`mt-1 font-semibold ${opsAlertTone}`}>Updated {opsSummary ? new Date(opsSummary.generated_at).toLocaleTimeString() : "-"}</div>
                <div className="mt-1">Users {opsSummary?.growth.users_total ?? 0} · New 7d {opsSummary?.growth.users_created_7d ?? 0}</div>
                <div>2FA {(opsSummary?.conversions.signup_to_twofa_verified_pct ?? 0).toFixed(1)}% · Broker {(opsSummary?.conversions.twofa_verified_to_broker_connected_pct ?? 0).toFixed(1)}%</div>
                <div>Exec submit {(opsSummary?.reliability.execution_submit_rate_pct ?? 0).toFixed(1)}% · error {(opsSummary?.reliability.execution_error_rate_pct ?? 0).toFixed(1)}%</div>
              </div>
              <div className="rounded border border-terminal-line bg-black/20 p-3 text-slate-300">
                <div className="text-[10px] uppercase tracking-wider text-slate-500">Mission Governance</div>
                <div className="mt-1">Style: {missionIntel?.mission.mission_style ?? "loading"}</div>
                <div>System Mode: {(missionIntel?.system_mode?.mode ?? "BALANCED").replaceAll("_", " ")}</div>
                <div>Confidence: {(missionIntel?.system_confidence?.score ?? 0).toFixed(2)} ({missionIntel?.system_confidence?.label ?? "LOW"})</div>
                <div>Parity: {missionIntel?.parity_watchdog.status ?? "N/A"}</div>
                <div>Truth 7d: Win {((truthDashboard?.win_rate ?? 0) * 100).toFixed(1)}% · PnL {(truthDashboard?.net_pnl ?? 0).toFixed(2)}</div>
              </div>
            </div>
          </details>
        </div>

        <aside className="space-y-4">
          <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3">
            <h3 className="text-[11px] font-semibold uppercase tracking-wider text-terminal-accent">Live Context</h3>
            <div className="mt-2">
              <BrokerStatusMiniCard broker={selectedBroker} />
            </div>
          </section>

          <ContextPanel context={contextSignal} />

          <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3">
            <h3 className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-terminal-accent">Controls</h3>
            <ControlPanel
              control={control}
              executionMode={executionMode}
              onToggleKillSwitch={handleToggleKillSwitch}
              onToggleAutonomous={handleToggleAutonomous}
              onRunAutonomousOnce={handleRunAutonomousOnce}
              onSetExecutionMode={handleSetExecutionMode}
              onUpdateLimits={handleUpdateLimits}
              onSetOptionsSprint={handleSetOptionsSprint}
            />
          </section>

          {(missionIntel?.parity_watchdog.issues?.length ?? 0) > 0 && missionIntel?.parity_watchdog.status !== "GREEN" && (
            <div className={`rounded-xl border px-3 py-3 text-xs ${missionIntel?.parity_watchdog.status === "RED" ? "border-red-500/40 bg-red-500/10 text-red-200" : "border-amber-500/40 bg-amber-500/10 text-amber-200"}`}>
              <div className="font-semibold">Parity Watchdog ({missionIntel?.parity_watchdog.status})</div>
              <ul className="mt-1 space-y-1">
                {missionIntel?.parity_watchdog.issues.slice(0, 4).map((issue) => (
                  <li key={issue}>{issue}</li>
                ))}
              </ul>
            </div>
          )}
        </aside>
      </section>

      {pendingClearOverrideStrategy && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/60 px-4" onClick={() => setPendingClearOverrideStrategy(null)}>
          <div
            className="w-full max-w-md rounded border border-terminal-line bg-[#081019] p-4 text-slate-200 shadow-xl"
            role="dialog"
            aria-modal="true"
            aria-labelledby="clear-override-modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            <h3 id="clear-override-modal-title" className="text-sm font-semibold text-terminal-accent">
              Confirm Override Clear
            </h3>
            <p className="mt-2 text-xs text-slate-300">
              Clear manual force-enable for <span className="font-semibold text-red-300">{pendingClearOverrideStrategy}</span>?
            </p>
            <p className="mt-1 text-[11px] text-slate-400">
              This allows the kill switch to disable it again if performance remains below threshold.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                ref={clearOverrideCancelButtonRef}
                type="button"
                onClick={() => setPendingClearOverrideStrategy(null)}
                className="rounded border border-terminal-line px-3 py-1.5 text-xs text-slate-300 hover:border-terminal-accent/60"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={Boolean(overrideBusyStrategy)}
                onClick={() => void confirmClearStrategyOverride()}
                className="rounded border border-red-500/40 bg-red-500/10 px-3 py-1.5 text-xs text-red-300 hover:bg-red-500/20 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Confirm Clear
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
