"use client";

import { useEffect, useState } from "react";

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
};

type Props = {
  control: ControlStatus | null;
  executionMode: "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING" | null;
  onToggleKillSwitch: (enabled: boolean) => void;
  onToggleAutonomous: (enabled: boolean) => void;
  onRunAutonomousOnce: () => void;
  onSetExecutionMode: (mode: "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING") => void;
  onUpdateLimits?: (data: { daily_loss_limit_pct: number; max_drawdown_limit_pct: number }) => Promise<void>;
};

export default function ControlPanel({
  control,
  executionMode,
  onToggleKillSwitch,
  onToggleAutonomous,
  onRunAutonomousOnce,
  onSetExecutionMode,
  onUpdateLimits,
}: Props) {
  const [pendingMode, setPendingMode] = useState<"SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING" | null>(null);
  const [editLimits, setEditLimits] = useState(false);
  const [draftDailyLoss, setDraftDailyLoss] = useState(5);
  const [draftMaxDrawdown, setDraftMaxDrawdown] = useState(10);
  const [limitsLoading, setLimitsLoading] = useState(false);

  useEffect(() => {
    if (control) {
      setDraftDailyLoss(parseFloat(((control.daily_loss_limit_pct ?? 0.05) * 100).toFixed(1)));
      setDraftMaxDrawdown(parseFloat((control.max_drawdown_limit_pct * 100).toFixed(1)));
    }
  }, [control]);

  if (!control) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading control status...</div>;
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
        await fetch(`${API_BASE}/control/limits`, {
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
  const drawdownUsedPct = control.max_drawdown_limit_pct > 0
    ? (control.rolling_drawdown_pct / control.max_drawdown_limit_pct) * 100
    : 0;

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Safety & Control</h3>
        <span className={`text-xs font-semibold ${control.system_status === "ACTIVE" ? "text-terminal-bull" : "text-terminal-bear"}`}>
          {control.system_status}
        </span>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-2 text-xs text-slate-300">
        <div className="rounded border border-terminal-line bg-black/20 p-2">Mode: {control.mode}</div>
        <div className={`rounded border bg-black/20 p-2 ${drawdownUsedPct > 80 ? "border-terminal-bear" : "border-terminal-line"}`}>
          Drawdown: {(control.rolling_drawdown_pct * 100).toFixed(2)}% / {(control.max_drawdown_limit_pct * 100).toFixed(0)}%
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Daily PnL: <span className={control.daily_pnl >= 0 ? "text-terminal-bull" : "text-terminal-bear"}>${control.daily_pnl.toFixed(2)}</span>
        </div>
        <div className={`rounded border bg-black/20 p-2 ${dailyLossUsedPct > 80 ? "border-terminal-bear" : "border-terminal-line"}`}>
          Loss: ${Math.abs(control.daily_loss).toFixed(2)} / ${control.daily_loss_limit.toFixed(2)}
          {dailyLossUsedPct > 60 && (
            <span className="ml-1 text-amber-300">({dailyLossUsedPct.toFixed(0)}%)</span>
          )}
        </div>
      </div>

      {/* Risk Limits Editor */}
      <div className="mb-3 rounded border border-terminal-line bg-black/20 p-3 text-xs text-slate-300">
        <div className="mb-2 flex items-center justify-between">
          <span className="font-semibold text-slate-400">Risk Limits</span>
          <button
            onClick={() => setEditLimits((v) => !v)}
            className="rounded border border-terminal-line px-2 py-0.5 text-[11px] text-terminal-accent hover:bg-terminal-accent/10"
          >
            {editLimits ? "Cancel" : "Edit"}
          </button>
        </div>
        {editLimits ? (
          <div className="space-y-2">
            <label className="flex items-center justify-between gap-2">
              <span className="text-slate-400">Daily Loss Limit %</span>
              <input
                type="number"
                min={0.5}
                max={50}
                step={0.5}
                value={draftDailyLoss}
                onChange={(e) => setDraftDailyLoss(Number(e.target.value))}
                className="w-20 rounded border border-terminal-line bg-black/40 px-2 py-1 text-right text-xs text-slate-200"
              />
            </label>
            <label className="flex items-center justify-between gap-2">
              <span className="text-slate-400">Max Drawdown Limit %</span>
              <input
                type="number"
                min={1}
                max={100}
                step={1}
                value={draftMaxDrawdown}
                onChange={(e) => setDraftMaxDrawdown(Number(e.target.value))}
                className="w-20 rounded border border-terminal-line bg-black/40 px-2 py-1 text-right text-xs text-slate-200"
              />
            </label>
            <button
              onClick={() => void saveLimits()}
              disabled={limitsLoading}
              className="rounded border border-terminal-bull bg-terminal-bull/10 px-3 py-1 text-xs text-terminal-bull disabled:opacity-50"
            >
              {limitsLoading ? "Saving…" : "Save Limits"}
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-1">
            <span>Daily Loss: {draftDailyLoss.toFixed(1)}%</span>
            <span>Max Drawdown: {draftMaxDrawdown.toFixed(1)}%</span>
          </div>
        )}
      </div>

      <button
        onClick={() => onToggleKillSwitch(!control.trading_enabled)}
        className={`mb-3 w-full rounded border px-3 py-2 text-sm font-semibold transition ${
          control.trading_enabled
            ? "border-terminal-bear bg-terminal-bear/15 text-terminal-bear"
            : "border-terminal-bull bg-terminal-bull/15 text-terminal-bull"
        }`}
      >
        {control.trading_enabled ? "Disable Trading (Kill Switch)" : "Enable Trading"}
      </button>

      <div className="mb-3 rounded border border-terminal-line bg-black/20 p-3 text-xs text-slate-300">
        <div className="mb-3 border-b border-terminal-line pb-3">
          <p className="mb-2 font-semibold text-slate-400">Execution Mode</p>
          <div className="flex flex-wrap gap-2">
            {(["SIMULATION", "PAPER_TRADING", "LIVE_TRADING"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => handleSelectMode(mode)}
                className={`rounded border px-2 py-1 text-[11px] font-semibold transition ${
                  executionMode === mode
                    ? "border-terminal-accent bg-terminal-accent/15 text-terminal-accent"
                    : "border-terminal-line bg-black/20 text-slate-300 hover:border-terminal-accent/50"
                }`}
              >
                {mode === "SIMULATION" ? "INSIGHT ONLY" : mode === "PAPER_TRADING" ? "PAPER" : "⚡ LIVE"}
              </button>
            ))}
          </div>
          {executionMode === "LIVE_TRADING" && (
            <p className="mt-2 font-semibold text-terminal-bear text-[11px]">
              ⚡ LIVE TRADING ACTIVE — real orders are being submitted.
            </p>
          )}
        </div>

        <div className="mb-2 flex items-center justify-between">
          <span className="font-semibold text-slate-400">Autonomous Execution</span>
          <span className={control.autonomous_enabled ? "text-terminal-bull" : "text-slate-400"}>
            {control.autonomous_enabled ? "ENABLED" : "DISABLED"}
          </span>
        </div>
        <p>Interval: {control.autonomous_interval_seconds}s</p>
        <p>Cycles run: {control.autonomous_cycles_run}</p>
        <p>Last run: {control.autonomous_last_run_at ? new Date(control.autonomous_last_run_at).toLocaleString() : "Never"}</p>
        {control.autonomous_last_error && <p className="mt-1 text-terminal-bear">{control.autonomous_last_error}</p>}

        <div className="mt-3 flex gap-2">
          <button
            onClick={() => onToggleAutonomous(!control.autonomous_enabled)}
            className={`rounded border px-3 py-2 text-xs font-semibold transition ${
              control.autonomous_enabled
                ? "border-terminal-bear bg-terminal-bear/15 text-terminal-bear"
                : "border-terminal-bull bg-terminal-bull/15 text-terminal-bull"
            }`}
          >
            {control.autonomous_enabled ? "Stop Auto Mode" : "Start Auto Mode"}
          </button>
          <button
            onClick={onRunAutonomousOnce}
            className="rounded border border-terminal-accent bg-terminal-accent/10 px-3 py-2 text-xs font-semibold text-terminal-accent transition"
          >
            Run Once
          </button>
        </div>
      </div>

      <div className="text-xs text-slate-300">
        <p className="mb-1 font-semibold text-slate-400">Recent Rejections</p>
        {control.rejected_trades.length === 0 && <p>No rejected trades yet.</p>}
        {control.rejected_trades.slice(-5).map((log, idx) => (
          <p key={`${log.timestamp}-${idx}`}>
            {log.symbol}: {log.reason}
          </p>
        ))}
      </div>

      {/* LIVE_TRADING Confirmation Modal */}
      {pendingMode === "LIVE_TRADING" && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
          <div className="mx-4 max-w-sm rounded-xl border border-terminal-bear bg-slate-950 p-6 shadow-2xl">
            <h2 className="mb-2 text-lg font-bold text-terminal-bear">⚡ Enable Live Trading?</h2>
            <p className="mb-4 text-sm text-slate-300">
              This will submit real orders through your connected broker. Capital is at risk. Confirm only if you
              intend to trade with real funds.
            </p>
            <div className="flex gap-3">
              <button
                onClick={confirmLiveMode}
                className="flex-1 rounded border border-terminal-bear bg-terminal-bear/20 py-2 text-sm font-bold text-terminal-bear hover:bg-terminal-bear/30"
              >
                Yes, Enable Live Trading
              </button>
              <button
                onClick={() => setPendingMode(null)}
                className="flex-1 rounded border border-terminal-line bg-black/30 py-2 text-sm text-slate-300 hover:bg-white/5"
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
