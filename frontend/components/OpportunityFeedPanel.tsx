"use client";

type Opportunity = {
  symbol: string;
  asset_class: string;
  region: string;
  regime: string;
  signal: string;
  consensus_bias: string;
  consensus_confidence: number;
  expected_return_pct: number;
  expected_value: number;
  risk_level: string;
  target_pct: number;
  recommended_notional: number;
  tradable: boolean;
  risk_adjusted_score: number;
  signal_validation?: {
    validated_signal_strength?: number;
    confirmation_count?: number;
  };
  market_reaction?: {
    correlation_score?: number;
  };
};
type CapitalSplit = {
  symbol: string;
  recommended_notional: number;
  allocation_weight: number;
};

type OpportunitiesPayload = {
  scanned: number;
  passed_prefilter: number;
  opportunities: Opportunity[];
  capital_allocation_recommendations: CapitalSplit[];
};

export default function OpportunityFeedPanel({ data }: { data: OpportunitiesPayload | null }) {
  if (!data) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading opportunity feed...</div>;
  }

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Opportunity Feed</h3>
        <span className="text-xs text-slate-300">
          {data.passed_prefilter}/{data.scanned} passed pre-filter
        </span>
      </div>

      <div className="mb-3 overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Symbol</th>
              <th className="px-2 py-1">Exp Ret</th>
              <th className="px-2 py-1">Risk Adj</th>
              <th className="px-2 py-1">EV</th>
              <th className="px-2 py-1">Valid</th>
              <th className="px-2 py-1">React</th>
              <th className="px-2 py-1">Risk</th>
              <th className="px-2 py-1">Target %</th>
            </tr>
          </thead>
          <tbody>
            {data.opportunities.length === 0 && (
              <tr>
                <td className="px-2 py-2 text-slate-400" colSpan={8}>
                  No candidates right now.
                </td>
              </tr>
            )}
            {data.opportunities.slice(0, 10).map((item) => (
              <tr key={item.symbol} className="border-t border-terminal-line">
                <td className="px-2 py-2">
                  <div className="flex items-center gap-2">
                    <span>{item.symbol}</span>
                    <span className="text-[10px] text-slate-500">{item.asset_class}</span>
                  </div>
                </td>
                <td className={`px-2 py-2 ${item.expected_return_pct >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                  {(item.expected_return_pct * 100).toFixed(2)}%
                </td>
                <td className="px-2 py-2">{item.risk_adjusted_score.toFixed(3)}</td>
                <td className="px-2 py-2">{item.expected_value.toFixed(4)}</td>
                <td className="px-2 py-2">{(item.signal_validation?.validated_signal_strength ?? 0).toFixed(2)}</td>
                <td className="px-2 py-2">{(item.market_reaction?.correlation_score ?? 0).toFixed(2)}</td>
                <td className="px-2 py-2">{item.risk_level}</td>
                <td className="px-2 py-2">{(item.target_pct * 100).toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-slate-300">
        <p className="mb-1 font-semibold text-slate-400">Allocation Engine Output</p>
        {data.capital_allocation_recommendations.length === 0 && (
          <p>No tradable setup allocation recommendations at the moment.</p>
        )}
        {data.capital_allocation_recommendations.slice(0, 6).map((row) => (
          <p key={row.symbol}>
            {row.symbol}: ${row.recommended_notional.toFixed(2)} ({(row.allocation_weight * 100).toFixed(1)}%)
          </p>
        ))}
      </div>
    </div>
  );
}
