type Signal = {
  signal: string;
  confidence: number;
  reasoning: string;
};

export default function SignalPanel({ signal }: { signal: Signal | null }) {
  if (!signal) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading signal engine...</div>;
  }

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <h3 className="mb-3 text-sm font-semibold text-terminal-accent">Strategy Recommendation</h3>
      <div className="mb-3 rounded-md border border-terminal-line bg-black/20 p-3">
        <div className="text-lg font-semibold">{signal.signal}</div>
        <div className="text-xs text-slate-300">Confidence: {Math.round(signal.confidence * 100)}%</div>
      </div>
      <p className="text-sm text-slate-300">{signal.reasoning}</p>
    </div>
  );
}
