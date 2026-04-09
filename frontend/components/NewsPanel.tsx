"use client";

type NewsSignal = {
  symbol: string;
  data_classification: "PUBLIC" | "DERIVED" | "RESTRICTED" | "UNKNOWN";
  sources_used: string[];
  sentiment_score: number;
  news_momentum_score: number;
  event_strength: number;
  event_flags: string[];
  rationale: string;
};

type NewsAuditEntry = {
  timestamp: string;
  symbol: string;
  sentiment_score: number;
  news_momentum_score: number;
  event_strength: number;
  event_flags: string[];
  sources_used: string[];
};

export default function NewsPanel({
  signal,
  audit,
}: {
  signal: NewsSignal | null;
  audit: NewsAuditEntry[] | null;
}) {
  if (!signal) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading news intelligence...</div>;
  }

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">News Intelligence</h3>
        <span className="text-xs text-slate-300">{signal.data_classification}</span>
      </div>

      <div className="mb-3 grid grid-cols-3 gap-2 text-xs text-slate-300">
        <div className="rounded border border-terminal-line bg-black/20 p-2">S: {signal.sentiment_score.toFixed(3)}</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">M: {signal.news_momentum_score.toFixed(3)}</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">E: {signal.event_strength.toFixed(3)}</div>
      </div>

      <div className="mb-3 text-xs text-slate-300">
        <p className="mb-1 font-semibold text-slate-400">Event Flags</p>
        <div className="flex flex-wrap gap-1">
          {signal.event_flags.map((flag) => (
            <span key={flag} className="rounded border border-terminal-line bg-black/20 px-2 py-0.5 text-[10px]">
              {flag}
            </span>
          ))}
        </div>
      </div>

      <div className="mb-3 text-xs text-slate-300">
        <p className="mb-1 font-semibold text-slate-400">Sources</p>
        <p>{signal.sources_used.join(", ")}</p>
      </div>

      <div className="text-xs text-slate-300">
        <p className="mb-1 font-semibold text-slate-400">Audit Trail (Recent)</p>
        {!audit || audit.length === 0 ? (
          <p className="text-slate-400">No audit rows yet.</p>
        ) : (
          <div className="space-y-1">
            {audit.slice(0, 5).map((entry) => (
              <p key={`${entry.symbol}-${entry.timestamp}`} className="text-[11px] text-slate-300">
                {new Date(entry.timestamp).toLocaleTimeString()} {entry.symbol} | S {entry.sentiment_score.toFixed(2)} | M {entry.news_momentum_score.toFixed(2)} | E {entry.event_strength.toFixed(2)}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
