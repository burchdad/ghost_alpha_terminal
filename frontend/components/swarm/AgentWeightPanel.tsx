"use client";

import React, { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Cell } from "recharts";

import { useSwarmStore } from "../../store/useSwarmStore";
import type { AgentWeightEntry, MarketRegime } from "../../types/swarm";

const REGIME_LABELS: Record<MarketRegime, string> = {
  TRENDING: "Trending",
  RANGE_BOUND: "Range Bound",
  HIGH_VOLATILITY: "High Volatility",
};

const REGIMES: MarketRegime[] = ["TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY"];

const AGENT_DISPLAY: Record<string, string> = {
  momentum_agent: "Momentum",
  mean_reversion_agent: "MeanRev",
  sentiment_agent: "Sentiment",
  volatility_agent: "Volatility",
  options_agent: "Options",
};

const AGENT_COLORS: Record<string, string> = {
  momentum_agent: "#6366f1",
  mean_reversion_agent: "#10b981",
  sentiment_agent: "#f59e0b",
  volatility_agent: "#ef4444",
  options_agent: "#3b82f6",
};

// Normalize bar chart data for a single regime
function toBarData(entries: AgentWeightEntry[]) {
  return entries.map((e) => ({
    name: AGENT_DISPLAY[e.agent_name] ?? e.agent_name,
    weight: parseFloat((e.weight * 100).toFixed(1)),
    rawScore: parseFloat(e.raw_score.toFixed(4)),
    fill: AGENT_COLORS[e.agent_name] ?? "#94a3b8",
  }));
}

// Build Recharts line data from history snapshots for a specific regime
function toLineData(snapshots: import("../../types/swarm").AgentWeightSnapshot[], regime: MarketRegime) {
  return snapshots
    .filter((s) => s.regime === regime)
    .slice(-40)
    .map((snap, i) => {
      const row: Record<string, string | number> = {
        tick: i + 1,
        cycle: snap.cycle_id.slice(0, 6),
      };
      for (const entry of snap.weights) {
        row[AGENT_DISPLAY[entry.agent_name] ?? entry.agent_name] = parseFloat(
          (entry.weight * 100).toFixed(1)
        );
      }
      return row;
    });
}

export default function AgentWeightPanel() {
  const { regimeWeights, weightHistory, fetchWeights } = useSwarmStore();
  const [activeRegime, setActiveRegime] = useState<MarketRegime>("TRENDING");
  const [view, setView] = useState<"current" | "trend">("current");
  const settledCycles = weightHistory?.total_settled_cycles ?? 0;
  const isBaselineOnly = settledCycles === 0;

  useEffect(() => {
    void fetchWeights();
    const handle = setInterval(() => void fetchWeights(), 15_000);
    return () => clearInterval(handle);
  }, [fetchWeights]);

  const currentEntries: AgentWeightEntry[] =
    regimeWeights?.regime_weights[activeRegime] ?? [];
  const barData = toBarData(currentEntries);

  const lineData = weightHistory
    ? toLineData(weightHistory.snapshots, activeRegime)
    : [];

  const hasHistory = lineData.length > 0;
  const agentKeys = Object.values(AGENT_DISPLAY);

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold text-white">Agent Weight Engine</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Dynamic influence per agent — updated on settled outcomes
          </p>
          <p className="text-[11px] text-slate-500 mt-0.5">
            Settled cycles: {settledCycles}
          </p>
        </div>
        <div className="flex gap-1.5">
          {(["current", "trend"] as const).map((v) => (
            <button
              key={v}
              onClick={() => setView(v)}
              className={`px-3 py-1 rounded-md text-xs font-medium transition-colors ${
                view === v
                  ? "bg-indigo-600 text-white"
                  : "text-slate-400 hover:text-white bg-white/5 hover:bg-white/10"
              }`}
            >
              {v === "current" ? "Current" : "Trend"}
            </button>
          ))}
        </div>
      </div>

      {/* Regime tabs */}
      <div className="flex gap-1.5 flex-wrap">
        {REGIMES.map((r) => (
          <button
            key={r}
            onClick={() => setActiveRegime(r)}
            className={`px-3 py-1 rounded-full text-xs font-medium transition-colors ${
              activeRegime === r
                ? "bg-indigo-600/80 text-white"
                : "text-slate-400 hover:text-slate-200 bg-white/5 hover:bg-white/10"
            }`}
          >
            {REGIME_LABELS[r]}
          </button>
        ))}
      </div>

      {/* Current weights — bar chart */}
      {view === "current" && (
        <>
          {isBaselineOnly && (
            <div className="rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
              Baseline mode: weights remain near default until outcomes are attached to completed cycles.
            </div>
          )}

          {/* Weight pills */}
          <div className="flex gap-3 flex-wrap">
            {currentEntries.map((e) => (
              <div
                key={e.agent_name}
                className="flex items-center gap-2 rounded-lg bg-white/5 border border-white/10 px-3 py-2"
              >
                <span
                  className="inline-block w-2 h-2 rounded-full"
                  style={{ backgroundColor: AGENT_COLORS[e.agent_name] ?? "#94a3b8" }}
                />
                <span className="text-xs text-slate-400">
                  {AGENT_DISPLAY[e.agent_name] ?? e.agent_name}
                </span>
                <span className="text-xs font-bold text-white">
                  {(e.weight * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>

          <ResponsiveContainer width="100%" height={180}>
            <BarChart
              data={barData}
              margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#94a3b8" }} />
              <YAxis
                domain={[0, 100]}
                tickFormatter={(v: number) => `${v}%`}
                tick={{ fontSize: 11, fill: "#94a3b8" }}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "#1e293b",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "8px",
                  fontSize: "12px",
                }}
                formatter={(val: number) => [`${val}%`, "Weight"]}
              />
              <Bar dataKey="weight" radius={[4, 4, 0, 0]}>
                {barData.map((entry, i) => (
                  <Cell key={`cell-${i}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>

          {/* Raw score table */}
          <div className="rounded-lg overflow-hidden border border-white/10">
            <table className="w-full text-xs">
              <thead className="bg-white/5 text-slate-400">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Agent</th>
                  <th className="px-3 py-2 text-right font-medium">Weight</th>
                  <th className="px-3 py-2 text-right font-medium">Raw Score</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {currentEntries.map((e) => (
                  <tr key={e.agent_name} className="hover:bg-white/5 transition-colors">
                    <td className="px-3 py-2 text-slate-200 flex items-center gap-2">
                      <span
                        className="inline-block w-1.5 h-1.5 rounded-full"
                        style={{ backgroundColor: AGENT_COLORS[e.agent_name] ?? "#94a3b8" }}
                      />
                      {AGENT_DISPLAY[e.agent_name] ?? e.agent_name}
                    </td>
                    <td className="px-3 py-2 text-right font-mono text-indigo-300">
                      {(e.weight * 100).toFixed(1)}%
                    </td>
                    <td
                      className={`px-3 py-2 text-right font-mono ${
                        e.raw_score >= 0 ? "text-emerald-400" : "text-red-400"
                      }`}
                    >
                      {e.raw_score >= 0 ? "+" : ""}
                      {e.raw_score.toFixed(4)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* Weight trend — line chart */}
      {view === "trend" && (
        <>
          {!hasHistory ? (
            <div className="flex items-center justify-center h-40 text-slate-500 text-sm">
              No settled outcomes yet — attach entry/exit prices to cycles to build weight history.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart
                data={lineData}
                margin={{ top: 4, right: 8, left: -16, bottom: 0 }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                  stroke="rgba(255,255,255,0.06)"
                />
                <XAxis
                  dataKey="tick"
                  tick={{ fontSize: 10, fill: "#94a3b8" }}
                  label={{
                    value: `${REGIME_LABELS[activeRegime]} outcomes`,
                    position: "insideBottom",
                    offset: -2,
                    fontSize: 10,
                    fill: "#64748b",
                  }}
                />
                <YAxis
                  domain={[0, 100]}
                  tickFormatter={(v: number) => `${v}%`}
                  tick={{ fontSize: 11, fill: "#94a3b8" }}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: "#1e293b",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  formatter={(val: number, name: string) => [
                    `${val}%`,
                    name,
                  ]}
                />
                <Legend
                  wrapperStyle={{ fontSize: "11px", paddingTop: "8px" }}
                />
                {agentKeys.map((key) => {
                  const agent = Object.entries(AGENT_DISPLAY).find(
                    ([, v]) => v === key
                  )?.[0];
                  return (
                    <Line
                      key={key}
                      type="monotone"
                      dataKey={key}
                      stroke={agent ? AGENT_COLORS[agent] : "#94a3b8"}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4 }}
                    />
                  );
                })}
              </LineChart>
            </ResponsiveContainer>
          )}

          <p className="text-xs text-slate-500 text-center">
            {weightHistory?.total_settled_cycles ?? 0} settled cycles tracked •
            showing last 40 in {REGIME_LABELS[activeRegime]}
          </p>
        </>
      )}
    </div>
  );
}
