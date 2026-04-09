"use client";

type ContextSignal = {
  symbol: string;
  data_classification: "PUBLIC" | "DERIVED" | "RESTRICTED" | "UNKNOWN";
  sources_used: string[];
  sentiment_score: number;
  news_momentum_score: number;
  event_strength: number;
  event_flags: string[];
  modifiers: {
    confidence_modifier: number;
    risk_modifier: number;
    opportunity_boost: number;
  };
  rationale: string;
};

export default function ContextPanel({ context }: { context: ContextSignal | null }) {
  if (!context) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading context intelligence...</div>;
  }

  const classColor =
    context.data_classification === "PUBLIC"
      ? "text-terminal-bull"
      : context.data_classification === "DERIVED"
      ? "text-terminal-accent"
      : context.data_classification === "UNKNOWN"
      ? "text-yellow-300"
      : "text-terminal-bear";

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Context Intelligence</h3>
        <span className={`text-xs font-semibold ${classColor}`}>{context.data_classification}</span>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-2 text-xs text-slate-300">
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Sentiment: {context.sentiment_score.toFixed(3)}
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Momentum: {context.news_momentum_score.toFixed(3)}
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Event: {context.event_strength.toFixed(3)}
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Boost: {context.modifiers.opportunity_boost.toFixed(3)}
        </div>
      </div>

      <div className="mb-2 text-xs text-slate-300">
        <p className="mb-1 font-semibold text-slate-400">Modifiers</p>
        <p>Confidence: {context.modifiers.confidence_modifier.toFixed(3)}x</p>
        <p>Risk: {context.modifiers.risk_modifier.toFixed(3)}x</p>
      </div>

      <div className="text-xs text-slate-300">
        <p className="mb-1 font-semibold text-slate-400">Sources</p>
        <p>{context.sources_used.join(", ")}</p>
        <p className="mt-2 text-slate-400">{context.rationale}</p>
      </div>
    </div>
  );
}
