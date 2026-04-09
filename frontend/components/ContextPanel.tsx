"use client";

type ContextSignal = {
  symbol: string;
  data_classification: "PUBLIC" | "DERIVED" | "RESTRICTED" | "UNKNOWN";
  sources_used: string[];
  sentiment_score: number;
  news_momentum_score: number;
  event_strength: number;
  event_flags: string[];
  signal_validation: {
    recency_decay_factor: number;
    average_source_weight: number;
    confirmation_count: number;
    confirmation_factor: number;
    confirmation_label: string;
    validated_signal_strength: number;
    source_details: Array<{
      source: string;
      source_weight: number;
      age_hours: number;
      decay_factor: number;
      effective_weight: number;
    }>;
  };
  market_reaction: {
    price_reaction_pct: number;
    volume_spike_ratio: number;
    breakout: string;
    expected_direction: string;
    price_direction: string;
    correlation_score: number;
    actionability_multiplier: number;
  };
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
        <p className="mb-1 font-semibold text-slate-400">Signal Validation</p>
        <p>Validated Strength: {context.signal_validation.validated_signal_strength.toFixed(3)}</p>
        <p>
          Confirmation: {context.signal_validation.confirmation_count} ({context.signal_validation.confirmation_label})
        </p>
        <p>Recency Decay: {context.signal_validation.recency_decay_factor.toFixed(3)}</p>
        <p>Source Credibility: {context.signal_validation.average_source_weight.toFixed(3)}</p>
      </div>

      <div className="mb-2 text-xs text-slate-300">
        <p className="mb-1 font-semibold text-slate-400">Market Reaction Correlation</p>
        <p>Price Reaction: {(context.market_reaction.price_reaction_pct * 100).toFixed(2)}%</p>
        <p>Volume Spike: {context.market_reaction.volume_spike_ratio.toFixed(2)}x</p>
        <p>
          Correlation: {context.market_reaction.correlation_score.toFixed(3)} ({context.market_reaction.expected_direction} vs {context.market_reaction.price_direction})
        </p>
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
