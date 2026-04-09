"use client";

type ReplayStep = {
  stage: string;
  title: string;
  summary: string;
  payload: Record<string, unknown>;
};

type ReplayPayload = {
  audit_id: string;
  symbol: string;
  decision_type: string;
  status: string;
  generated_at: string;
  replay_steps: ReplayStep[];
  why_not: string[];
};

export default function DecisionReplayPanel({ replay }: { replay: ReplayPayload | null }) {
  if (!replay) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Select an audit row to replay decision steps.</div>;
  }

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Decision Replay</h3>
        <span className={`text-xs ${replay.status === "ACCEPTED" ? "text-terminal-bull" : "text-terminal-bear"}`}>
          {replay.status}
        </span>
      </div>

      <p className="mb-3 text-xs text-slate-300">
        {replay.symbol} • {replay.decision_type} • {new Date(replay.generated_at).toLocaleString()}
      </p>

      <div className="space-y-2">
        {replay.replay_steps.map((step) => (
          <div key={step.stage} className="rounded border border-terminal-line bg-black/20 p-2">
            <p className="text-xs font-semibold text-terminal-accent">{step.title}</p>
            <p className="mb-1 text-[11px] text-slate-400">{step.summary}</p>
            <pre className="overflow-x-auto text-[10px] text-slate-300">{JSON.stringify(step.payload, null, 2)}</pre>
          </div>
        ))}
      </div>

      {replay.why_not.length > 0 && (
        <div className="mt-3 rounded border border-red-800/50 bg-red-950/20 p-2 text-xs text-red-200">
          <p className="mb-1 font-semibold">Why Not</p>
          {replay.why_not.map((line, idx) => (
            <p key={`${line}-${idx}`}>{line}</p>
          ))}
        </div>
      )}
    </div>
  );
}
