type BrokerPolicySummary = {
  policy: {
    equity_live: string;
    equity_live_weights: Record<string, number>;
    option_live_weights: Record<string, number>;
    crypto_live_weights: Record<string, number>;
  };
  brokers: Record<
    string,
    {
      execution_ready?: boolean;
      configured?: boolean;
      strengths?: string[];
      preferred_for?: string[];
      constraint?: string;
    }
  >;
  strategy_routing: Record<
    string,
    {
      active_candidates?: string[];
      selection_method?: string;
      constraint?: string;
    }
  >;
};

type Props = {
  policy: BrokerPolicySummary | null;
  selectedBrokerProvider: string | null;
};

function formatWeights(weights: Record<string, number>): string {
  const entries = Object.entries(weights);
  if (entries.length === 0) {
    return "none configured";
  }
  return entries.map(([broker, weight]) => `${broker}:${weight}`).join(" · ");
}

function toneForBroker(name: string, summary: BrokerPolicySummary | null, selectedBrokerProvider: string | null): string {
  if (selectedBrokerProvider === name) {
    return "border-terminal-accent/60 bg-terminal-accent/10 text-terminal-accent";
  }
  if (summary?.brokers[name]?.execution_ready) {
    return "border-green-500/30 bg-green-500/10 text-green-100";
  }
  if (summary?.brokers[name]?.configured) {
    return "border-cyan-500/30 bg-cyan-500/10 text-cyan-100";
  }
  return "border-slate-500/30 bg-slate-500/10 text-slate-300";
}

export default function BrokerPolicyPanel({ policy, selectedBrokerProvider }: Props) {
  if (!policy) {
    return (
      <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3 text-xs text-slate-400">
        Loading broker routing policy...
      </section>
    );
  }

  return (
    <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-terminal-accent">Routing Policy</h3>
        <span className="text-[10px] text-slate-500">Equities: {policy.policy.equity_live.replaceAll("_", " ")}</span>
      </div>

      <div className="space-y-2 text-[11px] text-slate-300">
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          <div className="font-semibold text-slate-100">Live Equity Weights</div>
          <div className="mt-1 text-slate-400">{formatWeights(policy.policy.equity_live_weights)}</div>
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          <div className="font-semibold text-slate-100">Live Option Weights</div>
          <div className="mt-1 text-slate-400">{formatWeights(policy.policy.option_live_weights)}</div>
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          <div className="font-semibold text-slate-100">Live Crypto Weights</div>
          <div className="mt-1 text-slate-400">{formatWeights(policy.policy.crypto_live_weights)}</div>
        </div>
      </div>

      <div className="mt-3 space-y-2">
        {Object.entries(policy.strategy_routing).map(([strategy, summary]) => (
          <div key={strategy} className="rounded border border-terminal-line bg-black/20 p-2 text-[11px] text-slate-300">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold uppercase tracking-wider text-slate-100">{strategy.replaceAll("_", " ")}</span>
              <span className="text-slate-500">{summary.selection_method?.replaceAll("_", " ") ?? "n/a"}</span>
            </div>
            <div className="mt-2 flex flex-wrap gap-1">
              {(summary.active_candidates ?? []).map((candidate) => (
                <span
                  key={`${strategy}-${candidate}`}
                  className={`rounded border px-1.5 py-0.5 text-[10px] ${toneForBroker(candidate, policy, selectedBrokerProvider)}`}
                >
                  {candidate}
                </span>
              ))}
              {(summary.active_candidates ?? []).length === 0 ? <span className="text-slate-500">No active candidates</span> : null}
            </div>
            {summary.constraint ? <div className="mt-2 text-[10px] text-amber-300">{summary.constraint}</div> : null}
          </div>
        ))}
      </div>

      <div className="mt-3 space-y-2">
        {Object.entries(policy.brokers).map(([broker, summary]) => (
          <div key={broker} className="rounded border border-terminal-line bg-black/20 p-2 text-[11px] text-slate-300">
            <div className="flex items-center justify-between gap-2">
              <span className="font-semibold capitalize text-slate-100">{broker}</span>
              <span className={summary.execution_ready ? "text-green-300" : summary.configured ? "text-cyan-300" : "text-slate-500"}>
                {summary.execution_ready ? "Execution Ready" : summary.configured ? "Configured" : "Not Ready"}
              </span>
            </div>
            {summary.strengths?.length ? <div className="mt-1 text-slate-400">Strengths: {summary.strengths.join(", ")}</div> : null}
            {summary.preferred_for?.length ? <div className="mt-1 text-slate-400">Best for: {summary.preferred_for.join(", ")}</div> : null}
            {summary.constraint ? <div className="mt-1 text-[10px] text-amber-300">{summary.constraint}</div> : null}
          </div>
        ))}
      </div>
    </section>
  );
}