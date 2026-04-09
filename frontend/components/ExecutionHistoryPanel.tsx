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

export default function ExecutionHistoryPanel({ history }: { history: ExecutionHistoryEntry[] | null }) {
  if (!history) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading execution history...</div>;
  }

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Execution History</h3>
        <span className="text-xs text-slate-300">Recent allocations + orders</span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Time</th>
              <th className="px-2 py-1">Symbol</th>
              <th className="px-2 py-1">Action</th>
              <th className="px-2 py-1">Mode</th>
              <th className="px-2 py-1">Alloc %</th>
              <th className="px-2 py-1">Qty</th>
              <th className="px-2 py-1">Notional</th>
              <th className="px-2 py-1">Outcome</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 && (
              <tr>
                <td className="px-2 py-2 text-slate-400" colSpan={8}>
                  No execution journal entries yet.
                </td>
              </tr>
            )}
            {history.slice(0, 8).map((item) => (
              <tr key={item.execution_id} className="border-t border-terminal-line align-top">
                <td className="px-2 py-2 text-slate-400">{new Date(item.timestamp).toLocaleTimeString()}</td>
                <td className="px-2 py-2">{item.symbol}</td>
                <td className="px-2 py-2">{item.action}</td>
                <td className="px-2 py-2">{item.mode}</td>
                <td className="px-2 py-2">{(item.allocation_pct * 100).toFixed(2)}%</td>
                <td className="px-2 py-2">{item.qty.toFixed(4)}</td>
                <td className="px-2 py-2">{item.notional.toFixed(2)}</td>
                <td className={`px-2 py-2 ${item.outcome_label === "WIN" ? "text-terminal-bull" : item.outcome_label === "LOSS" ? "text-terminal-bear" : "text-slate-300"}`}>
                  {item.outcome_label ?? (item.submitted ? "OPEN" : "LOGGED")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}