"use client";

import type { SwarmCycleResponse } from "../../types/swarm";

type Props = {
  latest: SwarmCycleResponse | null;
};

function actionStyle(action: string): string {
  if (action === "BUY") {
    return "text-terminal-bull";
  }
  if (action === "SELL") {
    return "text-terminal-bear";
  }
  return "text-slate-300";
}

export default function SwarmConsensusPanel({ latest }: Props) {
  if (!latest) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">No consensus cycle yet.</div>;
  }

  const rawMean =
    latest.agent_signals.length === 0
      ? 0
      : latest.agent_signals.reduce((sum, s) => sum + s.confidence, 0) / latest.agent_signals.length;

  const adjusted = latest.final_confidence;

  return (
    <div className="panel rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Consensus Panel</h3>
        <span className={`text-sm font-bold ${actionStyle(latest.final_action)}`}>{latest.final_action}</span>
      </div>

      <div className="grid grid-cols-1 gap-2 text-xs text-slate-300 md:grid-cols-2 xl:grid-cols-3">
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Final Confidence: {Math.round(latest.final_confidence * 100)}%
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Raw Mean Confidence: {Math.round(rawMean * 100)}%
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Adjusted Confidence: {Math.round(adjusted * 100)}%
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">Regime: {latest.regime}</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Risk Veto: {latest.vetoed ? "TRIGGERED" : "CLEAR"}
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Request ID: {latest.request_id || "N/A"}
        </div>
      </div>

      <p className="mt-3 text-xs text-slate-300">{latest.consensus_reasoning}</p>
      {latest.vetoed && latest.veto_reason && (
        <p className="mt-2 rounded border border-terminal-bear/40 bg-terminal-bear/10 p-2 text-xs text-terminal-bear">
          {latest.veto_reason}
        </p>
      )}
    </div>
  );
}
