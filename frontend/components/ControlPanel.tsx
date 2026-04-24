"use client";

import { useEffect, useRef, useState } from "react";
import { ensureHighTrust } from "../lib/highTrust";
import { apiFetch } from "../lib/apiClient";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type RejectedTrade = {
  timestamp: string;
  symbol: string;
  reason: string;
};

type ControlStatus = {
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
  rejected_trades: RejectedTrade[];
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

type Props = {
  control: ControlStatus | null;
  executionMode: "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING" | null;
  onToggleKillSwitch: (enabled: boolean) => void;
  onToggleAutonomous: (enabled: boolean) => void;
  onRunAutonomousOnce: () => void;
  onSetExecutionMode: (mode: "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING") => void;
  onUpdateLimits?: (data: { daily_loss_limit_pct: number; max_drawdown_limit_pct: number }) => Promise<void>;
  onSetOptionsSprint?: (enabled: boolean) => Promise<void>;
};

function RiskBar({ label, used, limit, value, limitLabel }: {
  label: string;
  used: number; // 0–100
  limit: number;
  value: string;
  limitLabel: string;
}) {
  const pct = Math.min(used, 100);
  const color =
    pct >= 90 ? "bg-red-500" :
    pct >= 70 ? "bg-amber-400" :
    pct >= 40 ? "bg-yellow-300" :
    "bg-terminal-bull";

  return (
    <div>
      <div className="mb-1 flex items-center justify-between text-[11px]">
        <span className="text-slate-400">{label}</span>
        <span className={pct >= 70 ? "font-semibold text-amber-300" : "text-slate-300"}>
          {value} <span className="text-slate-500">/ {limitLabel}</span>
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full transition-all duration-500 ${color}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function SectionHeader({ title, badge, badgeColor }: { title: string; badge?: string; badgeColor?: string }) {
  return (
    <div className="mb-2 flex items-center gap-2">
      <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500">{title}</span>
      <div className="flex-1 border-t border-terminal-line/40" />
      {badge && (
        <span className={`text-[10px] font-semibold ${badgeColor ?? "text-slate-400"}`}>{badge}</span>
      )}
    </div>
  );
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return "Never";
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  return new Date(iso).toLocaleDateString();
}

export default function ControlPanel({
  control,
  executionMode,
  onToggleKillSwitch,
  onToggleAutonomous,
  onRunAutonomousOnce,
  onSetExecutionMode,
  onUpdateLimits,
  onSetOptionsSprint,
}: Props) {
  const [pendingMode, setPendingMode] = useState<"SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING" | null>(null);
  const [editLimits, setEditLimits] = useState(false);
  const [draftDailyLoss, setDraftDailyLoss] = useState(5);
  const [draftMaxDrawdown, setDraftMaxDrawdown] = useState(10);
  const [limitsLoading, setLimitsLoading] = useState(false);
  const [rejectionsExpanded, setRejectionsExpanded] = useState(false);
  const killRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (control) {
      setDraftDailyLoss(parseFloat(((control.daily_loss_limit_pct ?? 0.05) * 100).toFixed(1)));
      setDraftMaxDrawdown(parseFloat((control.max_drawdown_limit_pct * 100).toFixed(1)));
    }
  }, [control]);

  if (!control) {
    return (
      <div className="panel rounded-xl p-4 text-sm text-slate-400 animate-pulse">
        Loading control status…
      </div>
    );
  }

  function handleSelectMode(mode: "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING") {
    if (mode === "LIVE_TRADING" && executionMode !== "LIVE_TRADING") {
      setPendingMode(mode);
    } else {
      onSetExecutionMode(mode);
    }
  }

  function confirmLiveMode() {
    if (pendingMode) {
      onSetExecutionMode(pendingMode);
      setPendingMode(null);
    }
  }

  async function saveLimits() {
    setLimitsLoading(true);
    try {
      if (onUpdateLimits) {
        await onUpdateLimits({
          daily_loss_limit_pct: draftDailyLoss / 100,
          max_drawdown_limit_pct: draftMaxDrawdown / 100,
        });
      } else {
        const ok = await ensureHighTrust({ apiBase: API_BASE });
        if (!ok) throw new Error("Security verification was cancelled");
        await apiFetch(`${API_BASE}/control/limits`, {
          apiBase: API_BASE,
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            daily_loss_limit_pct: draftDailyLoss / 100,
            max_drawdown_limit_pct: draftMaxDrawdown / 100,
          }),
        });
      }
      setEditLimits(false);
    } finally {
      setLimitsLoading(false);
    }
  }

  const dailyLossUsedPct =
    control.daily_loss_limit > 0 ? (Math.abs(control.daily_loss) / control.daily_loss_limit) * 100 : 0;
  const drawdownUsedPct =
    control.max_drawdown_limit_pct > 0
      ? (control.rolling_drawdown_pct / control.max_drawdown_limit_pct) * 100
      : 0;

  const modeConfig = {
    SIMULATION: {
      label: "INSIGHT ONLY",
      desc: "Signals & analysis — no orders placed",
      activeClass: "border-blue-500 bg-blue-500/10 text-blue-300",
      hoverClass: "hover:border-blue-500/40 hover:text-blue-200",
    },
    PAPER_TRADING: {
      label: "PAPER",
      desc: "Simulated orders, paper account",
      activeClass: "border-terminal-accent bg-terminal-accent/10 text-terminal-accent",
      hoverClass: "hover:border-terminal-accent/40 hover:text-terminal-accent/80",
    },
    LIVE_TRADING: {
      label: "⚡ LIVE",
      desc: "Real orders, real capital",
      activeClass: "border-terminal-bear bg-terminal-bear/10 text-terminal-bear",
      hoverClass: "hover:border-terminal-bear/40 hover:text-red-300",
    },
  } as const;

  const recentRejections = control.rejected_trades.slice(-10).reverse();
  const visibleRejections = rejectionsExpanded ? recentRejections : recentRejections.slice(0, 3);

  return (
    <div className="panel animate-riseIn space-y-4 rounded-xl p-4">

      {/* ── Header ───────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Safety & Control</h3>
        <div className="flex items-center gap-2">
          <span className={`h-2 w-2 rounded-full ${control.system_status === "ACTIVE" ? "animate-pulse bg-terminal-bull" : "bg-terminal-bear"}`} />
          <span className={`text-[11px] font-semibold ${control.system_status === "ACTIVE" ? "text-terminal-bull" : "text-terminal-bear"}`}>
            {control.system_status}
          </span>
          <span className="rounded border border-terminal-line/50 px-1.5 py-0.5 text-[10px] text-slate-500">
            {control.mode}
          </span>
        </div>
      </div>

      {/* ── P&L Summary ──────────────────────────────────────────── */}
      <div className="grid grid-cols-2 gap-3 text-xs">
        <div className="rounded-lg border border-terminal-line/60 bg-black/20 p-2.5">
          <div className="mb-0.5 text-[10px] uppercase tracking-wider text-slate-500">Daily P&amp;L</div>
          <div className={`text-base font-bold ${control.daily_pnl >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
            {control.daily_pnl >= 0 ? "+" : ""}${control.daily_pnl.toFixed(2)}
          </div>
        </div>
        <div className="rounded-lg border border-terminal-line/60 bg-black/20 p-2.5">
          <div className="mb-0.5 text-[10px] uppercase tracking-wider text-slate-500">Today&apos;s Loss</div>
          <div className={`text-base font-bold ${Math.abs(control.daily_loss) > 0 ? "text-terminal-bear" : "text-slate-300"}`}>
            ${Math.abs(control.daily_loss).toFixed(2)}
          </div>
        </div>
      </div>

      {/* ── Risk Progress Bars ───────────────────────────────────── */}
      <div className="space-y-3">
        <SectionHeader
          title="Risk Limits"
          badge={editLimits ? undefined : "Edit"}
          badgeColor="text-terminal-accent cursor-pointer"
        />
        {/* wrapper for Edit click on the badge — handled inline below */}
        <div>
          <RiskBar
            label="Daily Loss"
            used={dailyLossUsedPct}
            limit={control.daily_loss_limit}
            value={`$${Math.abs(control.daily_loss).toFixed(0)}`}
            limitLabel={`$${control.daily_loss_limit.toFixed(0)} (${draftDailyLoss.toFixed(1)}%)`}
          />
        </div>
        <div>
          <RiskBar
            label="Drawdown"
            used={drawdownUsedPct}
            limit={control.max_drawdown_limit_pct}
            value={`${(control.rolling_drawdown_pct * 100).toFixed(2)}%`}
            limitLabel={`${draftMaxDrawdown.toFixed(1)}%`}
          />
        </div>

        <button
          onClick={() => setEditLimits((v) => !v)}
          className="text-[11px] text-terminal-accent/70 underline underline-offset-2 hover:text-terminal-accent"
        >
          {editLimits ? "Cancel editing" : "Edit risk limits"}
        </button>

        {editLimits && (
          <div className="rounded-lg border border-terminal-line/60 bg-black/30 p-3 space-y-2">
            <label className="flex items-center justify-between gap-2 text-xs">
              <span className="text-slate-400">Daily Loss Limit %</span>
              <input
                type="number"
                min={0.5}
                max={50}
                step={0.5}
                value={draftDailyLoss}
                onChange={(e) => setDraftDailyLoss(Number(e.target.value))}
                className="w-20 rounded border border-terminal-line bg-black/50 px-2 py-1 text-right text-xs text-slate-200"
              />
            </label>
            <label className="flex items-center justify-between gap-2 text-xs">
              <span className="text-slate-400">Max Drawdown Limit %</span>
              <input
                type="number"
                min={1}
                max={100}
                step={1}
                value={draftMaxDrawdown}
                onChange={(e) => setDraftMaxDrawdown(Number(e.target.value))}
                className="w-20 rounded border border-terminal-line bg-black/50 px-2 py-1 text-right text-xs text-slate-200"
              />
            </label>
            <button
              onClick={() => void saveLimits()}
              disabled={limitsLoading}
              className="w-full rounded border border-terminal-bull bg-terminal-bull/10 py-1.5 text-xs font-semibold text-terminal-bull disabled:opacity-50 hover:bg-terminal-bull/20 transition"
            >
              {limitsLoading ? "Saving…" : "Save Limits"}
            </button>
          </div>
        )}
      </div>

      {/* ── Kill Switch ──────────────────────────────────────────── */}
      <div>
        <SectionHeader title="Master Switch" />
        <button
          ref={killRef}
          onClick={() => onToggleKillSwitch(!control.trading_enabled)}
          className={`w-full rounded-lg border px-4 py-2.5 text-sm font-bold transition-all active:scale-95 ${
            control.trading_enabled
              ? "border-terminal-bear/70 bg-terminal-bear/10 text-terminal-bear hover:bg-terminal-bear/20"
              : "border-terminal-bull/70 bg-terminal-bull/10 text-terminal-bull hover:bg-terminal-bull/20"
          }`}
        >
          {control.trading_enabled ? "🛑 Disable Trading (Kill Switch)" : "✅ Enable Trading"}
        </button>
        {!control.trading_enabled && (
          <p className="mt-1.5 text-center text-[11px] text-slate-500">Trading is halted — no orders will be submitted.</p>
        )}
      </div>

      {/* ── Execution Mode ───────────────────────────────────────── */}
      <div>
        <SectionHeader title="Execution Mode" />
        <div className="grid grid-cols-3 gap-1.5">
          {(["SIMULATION", "PAPER_TRADING", "LIVE_TRADING"] as const).map((mode) => {
            const cfg = modeConfig[mode];
            const active = executionMode === mode;
            return (
              <button
                key={mode}
                onClick={() => handleSelectMode(mode)}
                title={cfg.desc}
                className={`flex flex-col items-center gap-0.5 rounded-lg border px-2 py-2 text-center transition ${
                  active
                    ? cfg.activeClass
                    : `border-terminal-line/60 bg-black/20 text-slate-400 ${cfg.hoverClass}`
                }`}
              >
                <span className="text-[11px] font-bold">{cfg.label}</span>
                <span className="text-[9px] leading-tight opacity-70">{cfg.desc}</span>
              </button>
            );
          })}
        </div>
        {executionMode === "LIVE_TRADING" && (
          <div className="mt-2 flex items-center gap-2 rounded-lg border border-terminal-bear/40 bg-terminal-bear/5 px-3 py-2">
            <span className="animate-pulse text-base">⚡</span>
            <span className="text-[11px] font-semibold text-terminal-bear">
              LIVE TRADING ACTIVE — real orders are being submitted.
            </span>
          </div>
        )}
        {executionMode === "PAPER_TRADING" && (
          <p className="mt-1.5 text-[11px] text-slate-500 text-center">
            Simulated orders only. No real capital at risk.
          </p>
        )}
      </div>

      {/* ── Options Sprint ───────────────────────────────────────── */}
      <div>
        <SectionHeader
          title="Options Sprint"
          badge={control.options_sprint.enabled ? "ARMED" : "OFF"}
          badgeColor={control.options_sprint.enabled ? "text-amber-300" : "text-slate-500"}
        />
        <p className="mb-3 text-[11px] leading-relaxed text-slate-400">
          High-risk directional options profile for short-term expense-driven objectives.
        </p>
        {control.options_sprint.enabled && (
          <div className="mb-2 space-y-1 rounded-lg border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="text-slate-400">Live readiness</span>
              <span className={control.options_sprint.live_execution_ready ? "text-terminal-bull font-semibold" : "text-terminal-bear"}>
                {control.options_sprint.live_execution_ready ? "READY" : "BLOCKED"}
              </span>
            </div>
            {control.options_sprint.target_amount && (
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Target</span>
                <span className="text-slate-200">${control.options_sprint.target_amount.toLocaleString()}</span>
              </div>
            )}
            {control.options_sprint.timeframe_days && (
              <div className="flex items-center justify-between">
                <span className="text-slate-400">Window</span>
                <span className="text-slate-200">{control.options_sprint.timeframe_days} days</span>
              </div>
            )}
            {control.options_sprint.live_execution_blockers[0] && (
              <p className="pt-1 text-terminal-bear">{control.options_sprint.live_execution_blockers[0]}</p>
            )}
          </div>
        )}
        <div className="flex gap-2">
          <button
            onClick={() => void onSetOptionsSprint?.(true)}
            className="flex-1 rounded-lg border border-amber-500/60 bg-amber-500/10 py-2 text-[11px] font-semibold text-amber-300 transition hover:bg-amber-500/20 active:scale-95"
          >
            Arm Sprint
          </button>
          <button
            onClick={() => void onSetOptionsSprint?.(false)}
            disabled={!control.options_sprint.enabled}
            className="flex-1 rounded-lg border border-terminal-line/60 bg-black/20 py-2 text-[11px] font-semibold text-slate-300 transition hover:border-slate-500 disabled:opacity-40 active:scale-95"
          >
            Disarm
          </button>
        </div>
      </div>

      {/* ── Autonomous Execution ─────────────────────────────────── */}
      <div>
        <SectionHeader
          title="Autonomous Execution"
          badge={control.autonomous_enabled ? "ENABLED" : "DISABLED"}
          badgeColor={control.autonomous_enabled ? "text-terminal-bull" : "text-slate-500"}
        />
        <div className="mb-3 rounded-lg border border-terminal-line/60 bg-black/20 p-3 text-[11px] space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Cycle interval</span>
            <span className="text-slate-200">{control.autonomous_interval_seconds}s</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Cycles run</span>
            <span className="text-slate-200 font-semibold">{control.autonomous_cycles_run}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">Last run</span>
            <span className={`${!control.autonomous_last_run_at ? "text-slate-500" : "text-slate-200"}`}>
              {formatRelativeTime(control.autonomous_last_run_at)}
            </span>
          </div>
          {control.autonomous_enabled && (
            <div className="flex items-center gap-1.5 pt-1 text-terminal-bull">
              <span className="inline-block h-1.5 w-1.5 animate-pulse rounded-full bg-terminal-bull" />
              <span className="text-[10px]">Running automatically</span>
            </div>
          )}
          {control.autonomous_last_error && (
            <p className="pt-1 text-terminal-bear">{control.autonomous_last_error}</p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => onToggleAutonomous(!control.autonomous_enabled)}
            className={`flex-1 rounded-lg border py-2 text-xs font-bold transition active:scale-95 ${
              control.autonomous_enabled
                ? "border-terminal-bear/60 bg-terminal-bear/10 text-terminal-bear hover:bg-terminal-bear/20"
                : "border-terminal-bull/60 bg-terminal-bull/10 text-terminal-bull hover:bg-terminal-bull/20"
            }`}
          >
            {control.autonomous_enabled ? "Stop Auto Mode" : "Start Auto Mode"}
          </button>
          <button
            onClick={onRunAutonomousOnce}
            className="flex-1 rounded-lg border border-terminal-accent/60 bg-terminal-accent/10 py-2 text-xs font-bold text-terminal-accent transition hover:bg-terminal-accent/20 active:scale-95"
          >
            Run Once
          </button>
        </div>
      </div>

      {/* ── Recent Rejections ────────────────────────────────────── */}
      <div>
        <SectionHeader
          title="Recent Rejections"
          badge={recentRejections.length > 0 ? `${recentRejections.length}` : undefined}
          badgeColor="text-slate-500"
        />
        {recentRejections.length === 0 ? (
          <p className="text-[11px] text-slate-500">No rejected trades yet.</p>
        ) : (
          <div className="space-y-1">
            {visibleRejections.map((log, idx) => (
              <div
                key={`${log.timestamp}-${idx}`}
                className="flex items-start justify-between gap-2 rounded border border-terminal-line/30 bg-black/20 px-2 py-1.5 text-[11px]"
              >
                <div className="min-w-0 flex-1">
                  <span className="font-semibold text-terminal-bear">{log.symbol}</span>
                  <span className="ml-1 text-slate-400 truncate block">{log.reason}</span>
                </div>
                <span className="shrink-0 text-[10px] text-slate-600">
                  {log.timestamp ? formatRelativeTime(log.timestamp) : ""}
                </span>
              </div>
            ))}
            {recentRejections.length > 3 && (
              <button
                onClick={() => setRejectionsExpanded((v) => !v)}
                className="text-[11px] text-terminal-accent/60 underline underline-offset-2 hover:text-terminal-accent"
              >
                {rejectionsExpanded ? "Show less" : `Show ${recentRejections.length - 3} more`}
              </button>
            )}
          </div>
        )}
      </div>

      {/* ── Live Trading Confirmation Modal ──────────────────────── */}
      {pendingMode === "LIVE_TRADING" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm">
          <div className="mx-4 max-w-sm rounded-xl border border-terminal-bear bg-slate-950 p-6 shadow-2xl">
            <div className="mb-3 text-2xl text-center">⚡</div>
            <h2 className="mb-2 text-center text-lg font-bold text-terminal-bear">Enable Live Trading?</h2>
            <p className="mb-5 text-center text-sm leading-relaxed text-slate-300">
              Real orders will be submitted through your connected broker. Capital is at risk. Only confirm if you
              intend to trade with real funds.
            </p>
            <div className="flex gap-3">
              <button
                onClick={confirmLiveMode}
                className="flex-1 rounded-lg border border-terminal-bear bg-terminal-bear/20 py-2.5 text-sm font-bold text-terminal-bear hover:bg-terminal-bear/30 transition active:scale-95"
              >
                Yes, Go Live
              </button>
              <button
                onClick={() => setPendingMode(null)}
                className="flex-1 rounded-lg border border-terminal-line bg-black/30 py-2.5 text-sm text-slate-300 hover:bg-white/5 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
