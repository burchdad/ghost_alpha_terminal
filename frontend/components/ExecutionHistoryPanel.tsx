"use client";

import { useState } from "react";

const PAGE_SIZE = 10;

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
  const [page, setPage] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (!history) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading execution history...</div>;
  }

  const totalPages = Math.ceil(history.length / PAGE_SIZE);
  const pageItems = history.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  function outcomeClass(outcome: string | null) {
    if (outcome === "WIN") return "text-terminal-bull";
    if (outcome === "LOSS") return "text-terminal-bear";
    return "text-slate-300";
  }

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Execution History</h3>
        <span className="text-xs text-slate-300">
          {history.length} total entries
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Time</th>
              <th className="px-2 py-1">Symbol</th>
              <th className="px-2 py-1">Action</th>
              <th className="px-2 py-1">Strategy</th>
              <th className="px-2 py-1">Conf</th>
              <th className="px-2 py-1">Mode</th>
              <th className="px-2 py-1">Notional</th>
              <th className="px-2 py-1">PnL</th>
              <th className="px-2 py-1">Outcome</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 && (
              <tr>
                <td className="px-2 py-3 text-slate-400" colSpan={9}>
                  No execution journal entries yet.
                </td>
              </tr>
            )}
            {pageItems.map((item) => (
              <>
                <tr
                  key={item.execution_id}
                  className="cursor-pointer border-t border-terminal-line align-top hover:bg-white/5"
                  onClick={() => setExpandedId(expandedId === item.execution_id ? null : item.execution_id)}
                >
                  <td className="px-2 py-1.5 text-slate-400">
                    {new Date(item.timestamp).toLocaleDateString([], { month: "2-digit", day: "2-digit" })}{" "}
                    {new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </td>
                  <td className="px-2 py-1.5 font-semibold">{item.symbol}</td>
                  <td className="px-2 py-1.5">{item.action}</td>
                  <td className="px-2 py-1.5">{item.strategy}</td>
                  <td className="px-2 py-1.5">{Math.round(item.confidence * 100)}%</td>
                  <td className="px-2 py-1.5">{item.mode}</td>
                  <td className="px-2 py-1.5">${item.notional.toFixed(2)}</td>
                  <td className={`px-2 py-1.5 font-semibold ${item.pnl != null ? (item.pnl >= 0 ? "text-terminal-bull" : "text-terminal-bear") : "text-slate-400"}`}>
                    {item.pnl != null ? `${item.pnl >= 0 ? "+" : ""}$${item.pnl.toFixed(2)}` : "—"}
                  </td>
                  <td className={`px-2 py-1.5 font-semibold ${outcomeClass(item.outcome_label)}`}>
                    {item.outcome_label ?? (item.submitted ? "OPEN" : "LOGGED")}
                    {item.error ? " ⚠" : ""}
                  </td>
                </tr>
                {expandedId === item.execution_id && (
                  <tr key={`${item.execution_id}-detail`} className="border-b border-terminal-line bg-black/30">
                    <td colSpan={9} className="px-3 py-2 text-xs text-slate-300">
                      <div className="grid grid-cols-2 gap-x-6 gap-y-0.5 md:grid-cols-4">
                        <span><span className="text-slate-400">Cycle: </span>{item.cycle_id.slice(0, 8)}</span>
                        <span><span className="text-slate-400">Risk: </span>{item.risk_level}</span>
                        <span><span className="text-slate-400">Alloc: </span>{(item.allocation_pct * 100).toFixed(2)}%</span>
                        <span><span className="text-slate-400">Qty: </span>{item.qty.toFixed(6)}</span>
                        <span><span className="text-slate-400">Regime: </span>{item.regime}</span>
                        <span><span className="text-slate-400">Order: </span>{item.order_id ?? "none"}</span>
                        {item.reason && <span className="col-span-2"><span className="text-slate-400">Reason: </span>{item.reason}</span>}
                        {item.error && <span className="col-span-2 text-amber-300"><span className="text-slate-400">Error: </span>{item.error}</span>}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
          <span>
            Page {page + 1} / {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              disabled={page === 0}
              onClick={() => setPage((p) => p - 1)}
              className="rounded border border-terminal-line px-2 py-1 disabled:opacity-40 hover:text-terminal-accent"
            >
              Prev
            </button>
            <button
              disabled={page >= totalPages - 1}
              onClick={() => setPage((p) => p + 1)}
              className="rounded border border-terminal-line px-2 py-1 disabled:opacity-40 hover:text-terminal-accent"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
