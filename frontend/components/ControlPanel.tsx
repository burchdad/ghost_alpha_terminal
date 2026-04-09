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
};

type Props = {
  control: ControlStatus | null;
  onToggleKillSwitch: (enabled: boolean) => void;
};

export default function ControlPanel({ control, onToggleKillSwitch }: Props) {
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
