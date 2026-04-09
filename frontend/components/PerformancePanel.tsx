type AgentRow = {
  agent_name: string;
  accuracy: number;
  win_rate: number;
  avg_return: number;
  confidence_calibration: number;
  composite_score: number;
};

type StrategyRow = {
  strategy: string;
  trades: number;
  win_rate: number;
  avg_pnl: number;
};

type PerformanceData = {
  best_agent: string;
  agent_leaderboard: AgentRow[];
  top_strategies: StrategyRow[];
  by_regime: Record<string, { win_rate: number; avg_pnl: number; total_trades: number }>;
};

export default function PerformancePanel({ performance }: { performance: PerformanceData | null }) {
  if (!performance) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading performance feedback loop...</div>;
  }

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Learning Performance</h3>
        <span className="text-xs text-slate-300">Best: {performance.best_agent}</span>
      </div>

      <div className="mb-4 overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Agent</th>
              <th className="px-2 py-1">Win</th>
              <th className="px-2 py-1">Accuracy</th>
              <th className="px-2 py-1">Avg Return</th>
              <th className="px-2 py-1">Score</th>
            </tr>
          </thead>
          <tbody>
            {performance.agent_leaderboard.map((row) => (
              <tr key={row.agent_name} className="border-t border-terminal-line">
                <td className="px-2 py-1 font-semibold">{row.agent_name}</td>
                <td className="px-2 py-1">{Math.round(row.win_rate * 100)}%</td>
                <td className="px-2 py-1">{Math.round(row.accuracy * 100)}%</td>
                <td className="px-2 py-1">{(row.avg_return * 100).toFixed(2)}%</td>
                <td className="px-2 py-1">{Math.round(row.composite_score * 100)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h4 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Strategy Success Rates</h4>
      <div className="space-y-1 text-xs text-slate-300">
        {performance.top_strategies.length === 0 && <p>No trade outcomes recorded yet.</p>}
        {performance.top_strategies.map((strategy) => (
          <p key={strategy.strategy}>
            {strategy.strategy}: {Math.round(strategy.win_rate * 100)}% win, {strategy.trades} trades, avg pnl {strategy.avg_pnl.toFixed(3)}
          </p>
        ))}
      </div>

      <h4 className="mb-2 mt-4 text-xs font-semibold uppercase tracking-wide text-slate-400">Performance by Regime</h4>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Regime</th>
              <th className="px-2 py-1">Win Rate</th>
              <th className="px-2 py-1">Avg PnL</th>
              <th className="px-2 py-1">Trades</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(performance.by_regime).map(([regime, stats]) => (
              <tr key={regime} className="border-t border-terminal-line">
                <td className="px-2 py-1 font-semibold">{regime}</td>
                <td className="px-2 py-1">{Math.round(stats.win_rate * 100)}%</td>
                <td className="px-2 py-1">{stats.avg_pnl.toFixed(3)}</td>
                <td className="px-2 py-1">{stats.total_trades}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
