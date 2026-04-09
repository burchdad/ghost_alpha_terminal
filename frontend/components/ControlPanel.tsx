"use client";

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
};

export default function ControlPanel({
  control,
  executionMode,
  onToggleKillSwitch,
  onToggleAutonomous,
  onRunAutonomousOnce,
  onSetExecutionMode,
}: Props) {
  if (!control) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading control status...</div>;
  }

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
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Drawdown: {(control.rolling_drawdown_pct * 100).toFixed(2)}%
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">Daily PnL: {control.daily_pnl.toFixed(2)}</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Daily Loss: {control.daily_loss.toFixed(2)} / {control.daily_loss_limit.toFixed(2)}
        </div>
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
          <p className="mb-2 font-semibold text-slate-400">Execution Mode (Optional)</p>
          <div className="flex flex-wrap gap-2">
            {(["SIMULATION", "PAPER_TRADING", "LIVE_TRADING"] as const).map((mode) => (
              <button
                key={mode}
                onClick={() => onSetExecutionMode(mode)}
                className={`rounded border px-2 py-1 text-[11px] font-semibold transition ${
                  executionMode === mode
                    ? "border-terminal-accent bg-terminal-accent/15 text-terminal-accent"
                    : "border-terminal-line bg-black/20 text-slate-300"
                }`}
              >
                {mode === "SIMULATION" ? "INSIGHT ONLY" : mode === "PAPER_TRADING" ? "PAPER" : "LIVE"}
              </button>
            ))}
          </div>
          <p className="mt-2 text-[11px] text-slate-400">
            Insight-only mode logs recommendations without broker submission.
          </p>
        </div>

        <div className="mb-2 flex items-center justify-between">
          <span className="font-semibold text-slate-400">Autonomous Execution</span>
          <span className={control.autonomous_enabled ? "text-terminal-bull" : "text-slate-400"}>
            {control.autonomous_enabled ? "ENABLED" : "DISABLED"}
          </span>
        </div>
        <p>Interval: {control.autonomous_interval_seconds}s</p>
        <p>Universe source: top-ranked live scan candidates</p>
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
    </div>
  );
}
