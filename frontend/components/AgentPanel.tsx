type AgentPerformance = {
  accuracy: number;
  win_rate: number;
  avg_return: number;
  confidence_calibration: number;
  composite_score: number;
};

type AgentDecision = {
  agent_name: string;
  bias: "BULLISH" | "BEARISH" | "NEUTRAL";
  confidence: number;
  raw_confidence: number | null;
  adjusted_confidence: number | null;
  suggested_strategy: string;
  reasoning: string;
  performance: AgentPerformance | null;
  weighted_confidence: number | null;
};

type SwarmData = {
  regime: "TRENDING" | "RANGE_BOUND" | "HIGH_VOLATILITY";
  regime_confidence: number;
  consensus: {
    final_bias: "BULLISH" | "BEARISH" | "NEUTRAL";
    confidence: number;
    top_strategy: string;
  };
  recommended_trade: string;
  agent_breakdown: AgentDecision[];
};
// Extended fields from SwarmResponse that AgentPanel can optionally display
type SwarmDataExtended = SwarmData & {
  position_size?: number;
  risk_level?: "LOW" | "MEDIUM" | "HIGH";
  expected_value?: number;
};

export default function AgentPanel({ swarm }: { swarm: SwarmDataExtended | null }) {
  if (!swarm) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading swarm agents...</div>;
  }

  const biasColor =
    swarm.consensus.final_bias === "BULLISH"
      ? "text-terminal-bull"
      : swarm.consensus.final_bias === "BEARISH"
        ? "text-terminal-bear"
        : "text-terminal-warn";

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-terminal-accent">Swarm Consensus</h3>
        <span className={`text-xs font-semibold ${biasColor}`}>{swarm.consensus.final_bias}</span>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-2 text-xs text-slate-300 md:grid-cols-3">
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Confidence: {Math.round(swarm.consensus.confidence * 100)}%
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Top Strategy: {swarm.consensus.top_strategy}
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Recommended: {swarm.recommended_trade}
        </div>
      </div>

      {(swarm.position_size !== undefined || swarm.risk_level || swarm.expected_value !== undefined) && (
        <div className="mb-4 grid grid-cols-3 gap-2 text-xs text-slate-300">
          {swarm.position_size !== undefined && (
            <div className="rounded border border-terminal-line bg-black/20 p-2">
              <span className="text-slate-400">Size: </span>
              <span className="font-semibold text-slate-200">{(swarm.position_size * 100).toFixed(1)}%</span>
            </div>
          )}
          {swarm.risk_level && (
            <div className="rounded border border-terminal-line bg-black/20 p-2">
              <span className="text-slate-400">Risk: </span>
              <span
                className={`font-semibold ${swarm.risk_level === "LOW" ? "text-terminal-bull" : swarm.risk_level === "HIGH" ? "text-terminal-bear" : "text-terminal-warn"}`}
              >
                {swarm.risk_level}
              </span>
            </div>
          )}
          {swarm.expected_value !== undefined && (
            <div className="rounded border border-terminal-line bg-black/20 p-2">
              <span className="text-slate-400">EV: </span>
              <span className={`font-semibold ${swarm.expected_value >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                {swarm.expected_value >= 0 ? "+" : ""}
                {swarm.expected_value.toFixed(3)}
              </span>
            </div>
          )}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Agent</th>
              <th className="px-2 py-1">Bias</th>
              <th className="px-2 py-1">Raw Conf</th>
              <th className="px-2 py-1">Adj Conf</th>
              <th className="px-2 py-1">Strategy</th>
              <th className="px-2 py-1">Score</th>
              <th className="px-2 py-1">Weighted</th>
            </tr>
          </thead>
          <tbody>
            {swarm.agent_breakdown.map((agent) => (
              <tr key={agent.agent_name} className="border-t border-terminal-line align-top">
                <td className="px-2 py-2 font-semibold">{agent.agent_name}</td>
                <td className="px-2 py-2">{agent.bias}</td>
                <td className="px-2 py-2">{Math.round((agent.raw_confidence ?? agent.confidence) * 100)}%</td>
                <td className="px-2 py-2">{Math.round((agent.adjusted_confidence ?? agent.confidence) * 100)}%</td>
                <td className="px-2 py-2">{agent.suggested_strategy}</td>
                <td className="px-2 py-2">{Math.round((agent.performance?.composite_score ?? 0) * 100)}%</td>
                <td className="px-2 py-2">
                  {agent.weighted_confidence !== null && agent.weighted_confidence !== undefined
                    ? `${Math.round(agent.weighted_confidence * 100)}%`
                    : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-3 space-y-2 text-xs text-slate-300">
        {swarm.agent_breakdown.map((agent) => (
          <p key={`${agent.agent_name}-reason`}>
            <span className="font-semibold text-terminal-accent">{agent.agent_name}:</span> {agent.reasoning}
          </p>
        ))}
      </div>
    </div>
  );
}
