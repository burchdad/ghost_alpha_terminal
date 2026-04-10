"use client";

import { useState } from "react";

type StrategyType = "OPTIONS_PLAY" | "SWING_TRADE" | "DAY_TRADE" | "SCALP" | "WATCH" | "IGNORE";
type ActionLabel = "EXECUTE" | "SIMULATE" | "MONITOR" | "SKIP";

export type OrchestratorCandidate = {
  rank: number;
  symbol: string;
  asset_class: string;
  region: string;
  composite_score: number;
  strategy_type: StrategyType;
  action_label: ActionLabel;
  regime: string;
  consensus_bias: string;
  consensus_confidence: number;
  momentum_score: number;
  volume_spike: number;
  news_strength: number;
  volatility: number;
  expected_return_pct: number;
  risk_level: string;
  tradable: boolean;
  reasoning: string;
  why_trade_exists?: {
    persistence_bonus?: number;
    strategy_win_rate?: number;
    bucket_weight?: number;
    execution_quality?: number;
    strategy_state?: string;
  };
};

export type OrchestratorScan = {
  candidates: OrchestratorCandidate[];
  market_narrative: string;
  regime_summary: Record<string, number>;
  sector_leaders: string[];
  scanned_at: string;
  scan_count: number;
  total_scanned: number;
  passed_prefilter: number;
  auto_mode: boolean;
};

export type OrchestratorStatus = {
  auto_mode: boolean;
  auto_interval_seconds: number;
  scan_count: number;
  last_scan_at: string | null;
  top_pick: { symbol: string; strategy_type: string; composite_score: number } | null;
};

type Props = {
  scan: OrchestratorScan | null;
  status: OrchestratorStatus | null;
  loading: boolean;
  onScan: () => void;
  onToggleAutoMode: (enabled: boolean) => void;
  onRunSymbol: (symbol: string) => void;
};

const STRATEGY_CONFIG: Record<
  StrategyType,
  { label: string; color: string; bg: string; dot: string }
> = {
  OPTIONS_PLAY: {
    label: "OPTIONS",
    color: "text-purple-300",
    bg: "bg-purple-500/15 border-purple-500/40",
    dot: "bg-purple-400",
  },
  SWING_TRADE: {
    label: "SWING",
    color: "text-green-300",
    bg: "bg-green-500/15 border-green-500/40",
    dot: "bg-green-400",
  },
  DAY_TRADE: {
    label: "DAY",
    color: "text-yellow-300",
    bg: "bg-yellow-500/15 border-yellow-500/40",
    dot: "bg-yellow-400",
  },
  SCALP: {
    label: "SCALP",
    color: "text-orange-300",
    bg: "bg-orange-500/15 border-orange-500/40",
    dot: "bg-orange-400",
  },
  WATCH: {
    label: "WATCH",
    color: "text-slate-400",
    bg: "bg-slate-500/10 border-slate-500/30",
    dot: "bg-slate-500",
  },
  IGNORE: {
    label: "IGNORE",
    color: "text-slate-600",
    bg: "bg-slate-900/30 border-slate-700/20",
    dot: "bg-slate-700",
  },
};

const ACTION_CONFIG: Record<ActionLabel, { label: string; color: string }> = {
  EXECUTE: { label: "▶ EXECUTE", color: "text-green-400" },
  SIMULATE: { label: "⬡ SIMULATE", color: "text-blue-400" },
  MONITOR: { label: "◎ MONITOR", color: "text-yellow-500" },
  SKIP: { label: "— SKIP", color: "text-slate-600" },
};

const BIAS_COLORS: Record<string, string> = {
  BULLISH: "text-green-400",
  BEARISH: "text-red-400",
  NEUTRAL: "text-slate-400",
};

const REGIME_COLORS: Record<string, string> = {
  TRENDING: "text-blue-400",
  RANGE_BOUND: "text-yellow-400",
  HIGH_VOLATILITY: "text-red-400",
};

type FilterValue = StrategyType | "ALL";

export default function OrchestratorPanel({
  scan,
  status,
  loading,
  onScan,
  onToggleAutoMode,
  onRunSymbol,
}: Props) {
  const [filter, setFilter] = useState<FilterValue>("ALL");
  const [expanded, setExpanded] = useState(true);
  const [whyOpenBySymbol, setWhyOpenBySymbol] = useState<Record<string, boolean>>({});

  const candidates = scan?.candidates ?? [];
  const filtered =
    filter === "ALL" ? candidates : candidates.filter((c) => c.strategy_type === filter);
  const executeCount = candidates.filter((c) => c.action_label === "EXECUTE").length;
  const simulateCount = candidates.filter((c) => c.action_label === "SIMULATE").length;
  const autoEnabled = status?.auto_mode ?? false;

  return (
    <div className="rounded-xl border border-terminal-line bg-terminal-panel/80 p-4 mb-4">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-3">
          <button
            onClick={() => setExpanded((v) => !v)}
            className="text-terminal-accent hover:opacity-70 transition text-xs font-bold"
          >
            {expanded ? "▼" : "▶"}
          </button>
          <div>
            <h2 className="text-sm font-bold text-terminal-accent tracking-widest uppercase">
              GhostAlpha Intelligence Engine
            </h2>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {scan
                ? `${scan.total_scanned} tickers scanned → ${scan.passed_prefilter} passed → ${candidates.length} ranked  ·  scan #${scan.scan_count}`
                : "Awaiting first scan — press SCAN NOW to initialise"}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {/* Status pills */}
          {scan && (
            <>
              <span className="rounded border border-green-500/30 bg-green-500/10 px-2 py-0.5 text-[10px] font-semibold text-green-400">
                {executeCount} EXECUTE
              </span>
              <span className="rounded border border-blue-500/30 bg-blue-500/10 px-2 py-0.5 text-[10px] font-semibold text-blue-400">
                {simulateCount} SIMULATE
              </span>
            </>
          )}
          {/* Auto Mode toggle */}
          <button
            onClick={() => onToggleAutoMode(!autoEnabled)}
            className={`rounded border px-3 py-1 text-xs font-semibold transition ${
              autoEnabled
                ? "border-green-500/60 bg-green-500/15 text-green-400 hover:bg-green-500/25"
                : "border-terminal-line bg-black/20 text-slate-400 hover:border-slate-400/50 hover:text-slate-300"
            }`}
          >
            {autoEnabled ? "⚡ AUTO ON" : "○ AUTO OFF"}
          </button>
          {/* Scan Now */}
          <button
            onClick={onScan}
            disabled={loading}
            className="rounded border border-terminal-accent/60 bg-terminal-accent/10 px-4 py-1 text-xs font-bold text-terminal-accent transition hover:bg-terminal-accent/20 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? "SCANNING…" : "⟳ SCAN NOW"}
          </button>
        </div>
      </div>

      {!expanded && scan && (
        <p className="text-xs text-slate-400 truncate">
          Top pick:{" "}
          <span className="font-semibold text-terminal-accent">{candidates[0]?.symbol}</span>
          {" · "}
          <span className={STRATEGY_CONFIG[candidates[0]?.strategy_type ?? "WATCH"].color}>
            {STRATEGY_CONFIG[candidates[0]?.strategy_type ?? "WATCH"].label}
          </span>
          {" · "}
          {scan.market_narrative.slice(0, 120)}…
        </p>
      )}

      {expanded && (
        <>
          {/* ── Market Narrative ──────────────────────────────────────────── */}
          {scan && (
            <div className="rounded-lg border border-terminal-line/40 bg-black/30 px-4 py-3 mb-4">
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-[10px] font-bold tracking-widest text-terminal-accent uppercase">
                  Market Narrative
                </span>
                <span className="text-[10px] text-slate-600">
                  {new Date(scan.scanned_at).toLocaleTimeString()}
                </span>
              </div>
              <p className="text-sm text-slate-300 leading-relaxed">{scan.market_narrative}</p>

              {/* Regime breakdown */}
              <div className="mt-3 flex flex-wrap gap-2">
                {Object.entries(scan.regime_summary).map(([regime, count]) => (
                  <span
                    key={regime}
                    className={`text-[10px] font-medium ${REGIME_COLORS[regime] ?? "text-slate-400"}`}
                  >
                    <span className="text-slate-600 mr-0.5">{regime.replace("_", " ")}:</span>
                    {count}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* ── Strategy Filter Tabs ──────────────────────────────────────── */}
          {scan && (
            <div className="flex flex-wrap gap-1.5 mb-3">
              {(
                [
                  "ALL",
                  "OPTIONS_PLAY",
                  "SWING_TRADE",
                  "DAY_TRADE",
                  "SCALP",
                  "WATCH",
                ] as FilterValue[]
              ).map((f) => {
                const cfg = f !== "ALL" ? STRATEGY_CONFIG[f] : null;
                const active = filter === f;
                const count =
                  f === "ALL"
                    ? candidates.length
                    : candidates.filter((c) => c.strategy_type === f).length;
                return (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`rounded border px-2.5 py-1 text-[10px] font-semibold transition ${
                      active
                        ? cfg
                          ? `${cfg.bg} ${cfg.color}`
                          : "border-terminal-accent/50 bg-terminal-accent/10 text-terminal-accent"
                        : "border-terminal-line/40 bg-black/20 text-slate-600 hover:text-slate-400"
                    }`}
                  >
                    {f === "ALL" ? "ALL" : STRATEGY_CONFIG[f as StrategyType].label}
                    <span className="ml-1 opacity-60">{count}</span>
                  </button>
                );
              })}
            </div>
          )}

          {/* ── Candidates Table ─────────────────────────────────────────── */}
          {scan ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-terminal-line/30 text-[10px] text-slate-600 uppercase tracking-wider">
                    <th className="pb-2 pr-2 text-left font-medium w-6">#</th>
                    <th className="pb-2 pr-3 text-left font-medium">Ticker</th>
                    <th className="pb-2 pr-3 text-left font-medium">Score</th>
                    <th className="pb-2 pr-3 text-left font-medium">Strategy</th>
                    <th className="pb-2 pr-3 text-left font-medium hidden lg:table-cell">Regime</th>
                    <th className="pb-2 pr-3 text-left font-medium hidden xl:table-cell">Bias</th>
                    <th className="pb-2 pr-3 text-left font-medium hidden lg:table-cell">News</th>
                    <th className="pb-2 pr-3 text-left font-medium hidden xl:table-cell">Vol</th>
                    <th className="pb-2 pr-3 text-left font-medium">Action</th>
                    <th className="pb-2 text-right font-medium">Run</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((c) => {
                    const strCfg = STRATEGY_CONFIG[c.strategy_type];
                    const actCfg = ACTION_CONFIG[c.action_label];
                    const isActionable =
                      c.action_label === "EXECUTE" || c.action_label === "SIMULATE";
                    return (
                      <>
                        <tr
                          key={c.symbol}
                          className="border-b border-terminal-line/15 hover:bg-white/[0.025] transition"
                          title={c.reasoning}
                        >
                          <td className="py-2 pr-2 text-slate-700">{c.rank}</td>
                          <td className="py-2 pr-3">
                            <div className="flex items-center gap-1.5">
                              <span className={`h-1.5 w-1.5 rounded-full flex-shrink-0 ${strCfg.dot}`} />
                              <span className="font-bold text-slate-100">{c.symbol}</span>
                            </div>
                            <div className="text-[9px] text-slate-600 mt-0.5 hidden xl:block">
                              {c.asset_class} · {c.region}
                            </div>
                          </td>

                          {/* Score bar */}
                          <td className="py-2 pr-3">
                            <div className="flex items-center gap-1.5">
                              <div className="h-1.5 w-12 rounded-full bg-black/50">
                                <div
                                  className="h-1.5 rounded-full bg-terminal-accent"
                                  style={{ width: `${Math.round(c.composite_score * 100)}%` }}
                                />
                              </div>
                              <span className="text-terminal-accent font-semibold">
                                {Math.round(c.composite_score * 100)}
                              </span>
                            </div>
                          </td>

                          {/* Strategy badge */}
                          <td className="py-2 pr-3">
                            <span
                              className={`rounded border px-1.5 py-0.5 text-[9px] font-bold tracking-wide ${strCfg.bg} ${strCfg.color}`}
                            >
                              {strCfg.label}
                            </span>
                          </td>

                          <td
                            className={`py-2 pr-3 hidden lg:table-cell text-[10px] ${REGIME_COLORS[c.regime] ?? "text-slate-500"}`}
                          >
                            {c.regime.replace("_", " ")}
                          </td>
                          <td
                            className={`py-2 pr-3 hidden xl:table-cell font-semibold ${BIAS_COLORS[c.consensus_bias] ?? "text-slate-400"}`}
                          >
                            {c.consensus_bias}
                          </td>

                          {/* News bar */}
                          <td className="py-2 pr-3 hidden lg:table-cell">
                            <div className="h-1 w-10 rounded-full bg-black/40">
                              <div
                                className="h-1 rounded-full bg-blue-400/70"
                                style={{
                                  width: `${Math.min(100, Math.round(c.news_strength * 200))}%`,
                                }}
                              />
                            </div>
                          </td>

                          <td className="py-2 pr-3 hidden xl:table-cell text-slate-500">
                            {(c.volatility * 100).toFixed(1)}%
                          </td>

                          {/* Action */}
                          <td className={`py-2 pr-3 font-semibold text-[10px] ${actCfg.color}`}>
                            {actCfg.label}
                          </td>

                          {/* Run button */}
                          <td className="py-2 text-right">
                            <div className="flex items-center justify-end gap-1.5">
                              <button
                                onClick={() =>
                                  setWhyOpenBySymbol((current) => ({
                                    ...current,
                                    [c.symbol]: !current[c.symbol],
                                  }))
                                }
                                className="rounded border border-blue-500/40 bg-blue-500/10 px-2 py-0.5 text-[10px] font-semibold text-blue-300 hover:bg-blue-500/20 transition"
                              >
                                WHY
                              </button>
                              {isActionable && (
                                <button
                                  onClick={() => onRunSymbol(c.symbol)}
                                  className="rounded border border-terminal-accent/40 bg-terminal-accent/10 px-2.5 py-0.5 text-[10px] font-bold text-terminal-accent hover:bg-terminal-accent/25 transition"
                                >
                                  ▶ RUN
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                        {whyOpenBySymbol[c.symbol] && (
                          <tr key={`${c.symbol}-why`} className="border-b border-terminal-line/10 bg-black/20">
                            <td colSpan={10} className="px-2 py-2 text-[11px] text-slate-300">
                              <div className="font-semibold text-terminal-accent">Why This Trade Exists</div>
                              <div className="mt-1 grid grid-cols-1 gap-1 md:grid-cols-2 xl:grid-cols-3">
                                <div>
                                  Persistence bonus: <span className="text-green-300">{(c.why_trade_exists?.persistence_bonus ?? 0).toFixed(4)}</span>
                                </div>
                                <div>
                                  Strategy win rate: <span className="text-green-300">{((c.why_trade_exists?.strategy_win_rate ?? 0) * 100).toFixed(1)}%</span>
                                </div>
                                <div>
                                  Bucket weight: <span className="text-blue-300">{((c.why_trade_exists?.bucket_weight ?? 0) * 100).toFixed(1)}%</span>
                                </div>
                                <div>
                                  Execution quality: <span className="text-cyan-300">{((c.why_trade_exists?.execution_quality ?? 0) * 100).toFixed(1)}%</span>
                                </div>
                                <div>
                                  Strategy state: <span className={`${(c.why_trade_exists?.strategy_state ?? "enabled") === "disabled" ? "text-red-300" : (c.why_trade_exists?.strategy_state ?? "enabled") === "probation" ? "text-amber-300" : "text-green-300"}`}>{c.why_trade_exists?.strategy_state ?? "enabled"}</span>
                                </div>
                              </div>
                              <div className="mt-1 text-slate-500">{c.reasoning}</div>
                            </td>
                          </tr>
                        )}
                      </>
                    );
                  })}
                </tbody>
              </table>

              {filtered.length === 0 && (
                <p className="py-6 text-center text-xs text-slate-600">
                  No candidates match this filter.
                </p>
              )}
            </div>
          ) : !loading ? (
            <div className="py-10 text-center">
              <p className="text-xs text-slate-600 mb-3">
                No scan data yet. The intelligence engine scans all 321 universe tickers,
                <br />
                scores them, selects the optimal strategy per candidate, and ranks them.
              </p>
              <button
                onClick={onScan}
                className="rounded border border-terminal-accent/50 bg-terminal-accent/10 px-5 py-2 text-xs font-bold text-terminal-accent hover:bg-terminal-accent/20 transition"
              >
                ⟳ RUN FIRST SCAN
              </button>
            </div>
          ) : (
            <div className="py-10 text-center text-xs text-slate-600 animate-pulse">
              Scanning universe…
            </div>
          )}
        </>
      )}
    </div>
  );
}
