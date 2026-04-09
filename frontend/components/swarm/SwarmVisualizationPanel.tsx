"use client";

import { useEffect, useMemo, useState } from "react";

import { useSwarmStore } from "../../store/useSwarmStore";
import type { MarketRegime } from "../../types/swarm";
import SwarmConsensusPanel from "./SwarmConsensusPanel";
import SwarmDecisionTimeline from "./SwarmDecisionTimeline";
import SwarmGraphView from "./SwarmGraphView";
import SwarmLeaderboard from "./SwarmLeaderboard";
import AgentWeightPanel from "./AgentWeightPanel";

type Props = {
  symbol: string;
  regime: MarketRegime;
  regimeConfidence: number;
  forecastPrices: number[];
  currentPrice: number;
};

function buildCyclePayload(
  symbol: string,
  regime: MarketRegime,
  regimeConfidence: number,
  forecastPrices: number[],
  currentPrice: number,
) {
  const close_prices =
    forecastPrices.length >= 2
      ? forecastPrices.map((v) => Number(v.toFixed(4)))
      : [
          currentPrice * 0.985,
          currentPrice * 0.992,
          currentPrice,
          currentPrice * 1.004,
          currentPrice * 1.009,
          currentPrice * 1.012,
        ].map((v) => Number(v.toFixed(4)));

  const volumes = close_prices.map((_, i) => 1_000_000 + i * 15_000);

  return {
    symbol,
    close_prices,
    volumes,
    regime,
    regime_confidence: regimeConfidence,
    qty: 1,
  };
}

export default function SwarmVisualizationPanel({
  symbol,
  regime,
  regimeConfidence,
  forecastPrices,
  currentPrice,
}: Props) {
  const {
    loading,
    runningCycle,
    error,
    decisions,
    status,
    transport,
    websocketConnected,
    executionMode,
    fetchStatus,
    fetchDecisions,
    runCycle,
    setExecutionMode,
    updateOutcome,
    startLive,
    stopLive,
  } = useSwarmStore();

  const [entryPrice, setEntryPrice] = useState("");
  const [exitPrice, setExitPrice] = useState("");

  const latest = decisions[0] ?? null;

  const latestSignals = useMemo(() => latest?.agent_signals ?? [], [latest]);

  useEffect(() => {
    void fetchStatus();
    void fetchDecisions(150);
    startLive();
    return () => stopLive();
  }, [fetchStatus, fetchDecisions, startLive, stopLive]);

  async function handleRunCycle() {
    const payload = buildCyclePayload(symbol, regime, regimeConfidence, forecastPrices, currentPrice);
    await runCycle(payload);
  }

  async function handleOutcomeSubmit() {
    if (!latest) {
      return;
    }
    const entry = Number(entryPrice);
    const exit = Number(exitPrice);
    if (!Number.isFinite(entry) || !Number.isFinite(exit) || entry <= 0 || exit <= 0) {
      return;
    }
    await updateOutcome(latest.cycle_id, { entry_price: entry, exit_price: exit });
    setEntryPrice("");
    setExitPrice("");
  }

  return (
    <div className="space-y-4">
      <div className="panel rounded-xl p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-sm font-semibold text-terminal-accent">Swarm Visualization Layer</h2>
          <div className="flex items-center gap-3 text-xs text-slate-300">
            <span>
              Live: {transport.toUpperCase()} {websocketConnected ? "(WS connected)" : "(polling fallback)"}
            </span>
            <span>Total cycles: {status?.total_cycles ?? 0}</span>
            <select
              value={executionMode}
              onChange={(e) => void setExecutionMode(e.target.value as typeof executionMode)}
              className="rounded border border-terminal-line bg-black/20 px-2 py-1 text-xs text-slate-200"
            >
              <option value="SIMULATION">SIMULATION</option>
              <option value="PAPER_TRADING">PAPER TRADING</option>
              <option value="LIVE_TRADING">LIVE TRADING</option>
            </select>
            <button
              onClick={handleRunCycle}
              disabled={runningCycle}
              className="rounded border border-terminal-line px-3 py-1 text-terminal-accent hover:bg-terminal-accent/10 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {runningCycle ? "Running..." : "Run Swarm Cycle"}
            </button>
          </div>
        </div>
        {error && <p className="mt-2 text-xs text-terminal-bear">{error}</p>}
      </div>

      <div className="panel rounded-xl p-4">
        <h3 className="mb-2 text-sm font-semibold text-terminal-accent">Outcome Tracking</h3>
        <div className="flex flex-wrap items-end gap-2 text-xs">
          <label className="flex flex-col gap-1 text-slate-300">
            Entry Price
            <input
              value={entryPrice}
              onChange={(e) => setEntryPrice(e.target.value)}
              placeholder="e.g. 188.25"
              className="rounded border border-terminal-line bg-black/20 px-2 py-1 text-slate-100"
            />
          </label>
          <label className="flex flex-col gap-1 text-slate-300">
            Exit Price
            <input
              value={exitPrice}
              onChange={(e) => setExitPrice(e.target.value)}
              placeholder="e.g. 191.40"
              className="rounded border border-terminal-line bg-black/20 px-2 py-1 text-slate-100"
            />
          </label>
          <button
            onClick={handleOutcomeSubmit}
            disabled={!latest}
            className="rounded border border-terminal-line px-3 py-1 text-terminal-accent hover:bg-terminal-accent/10 disabled:cursor-not-allowed disabled:opacity-60"
          >
            Attach Outcome To Latest Cycle
          </button>
        </div>
        {latest?.outcome && (
          <p className="mt-2 text-xs text-slate-300">
            Latest outcome: {latest.outcome.outcome_label} | PnL {latest.outcome.pnl.toFixed(3)} | Entry {latest.outcome.entry_price.toFixed(3)} → Exit {latest.outcome.exit_price.toFixed(3)}
          </p>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 2xl:grid-cols-2">
        <SwarmGraphView signals={latestSignals} />
        <SwarmConsensusPanel latest={latest} />
      </div>

      <SwarmDecisionTimeline decisions={decisions} />
      <AgentWeightPanel />
      <SwarmLeaderboard decisions={decisions} />

      {loading && <div className="text-xs text-slate-400">Refreshing swarm decisions...</div>}
    </div>
  );
}
