"use client";

import { useMemo, useState } from "react";
import { ResponsiveContainer, Tooltip, XAxis, YAxis, ScatterChart, Scatter, CartesianGrid } from "recharts";

import type { SwarmCycleResponse } from "../../types/swarm";

type Props = {
  decisions: SwarmCycleResponse[];
};

const actionScore: Record<string, number> = {
  BUY: 1,
  HOLD: 0,
  SELL: -1,
};

export default function SwarmDecisionTimeline({ decisions }: Props) {
  const [visibleCount, setVisibleCount] = useState(25);

  const timeline = useMemo(
    () =>
      [...decisions]
        .reverse()
        .map((d, idx) => ({
          idx,
          ts: new Date(d.timestamp).toLocaleTimeString(),
          symbol: d.symbol,
          regime: d.regime,
          action: d.final_action,
          actionValue: actionScore[d.final_action] ?? 0,
          confidencePct: Math.round(d.final_confidence * 100),
        })),
    [decisions],
  );

  const virtualRows = useMemo(() => decisions.slice(0, visibleCount), [decisions, visibleCount]);

  return (
    <div className="panel rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Decision Timeline</h3>
        <span className="text-xs text-slate-300">{decisions.length} cycles</span>
      </div>

      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="idx" tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <YAxis domain={[-1, 1]} tick={{ fill: "#94a3b8", fontSize: 11 }} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              contentStyle={{ background: "#0f172a", border: "1px solid #1e293b", color: "#cbd5e1" }}
            />
            <Scatter data={timeline} fill="#38bdf8" />
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      <div className="mt-3 max-h-64 overflow-y-auto rounded border border-terminal-line">
        <table className="min-w-full text-left text-xs">
          <thead className="sticky top-0 bg-slate-950 text-slate-400">
            <tr>
              <th className="px-2 py-2">Timestamp</th>
              <th className="px-2 py-2">Symbol</th>
              <th className="px-2 py-2">Regime</th>
              <th className="px-2 py-2">Action</th>
              <th className="px-2 py-2">Confidence</th>
            </tr>
          </thead>
          <tbody>
            {virtualRows.map((d) => (
              <tr key={d.cycle_id} className="border-t border-terminal-line text-slate-300">
                <td className="px-2 py-2">{new Date(d.timestamp).toLocaleString()}</td>
                <td className="px-2 py-2">{d.symbol}</td>
                <td className="px-2 py-2">{d.regime}</td>
                <td className="px-2 py-2">{d.final_action}</td>
                <td className="px-2 py-2">{Math.round(d.final_confidence * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {visibleCount < decisions.length && (
        <button
          onClick={() => setVisibleCount((v) => Math.min(v + 25, decisions.length))}
          className="mt-3 rounded border border-terminal-line px-3 py-1 text-xs text-terminal-accent hover:bg-terminal-accent/10"
        >
          Load more
        </button>
      )}
    </div>
  );
}
