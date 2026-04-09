type ActivePosition = {
  symbol: string;
  strategy: string;
  side: string;
  entry_price: number;
  units: number;
  notional: number;
  sector: string;
  opened_at: string;
};

type PortfolioData = {
  account_balance: number;
  active_positions: ActivePosition[];
  total_exposure: number;
  risk_exposure_pct: number;
  sector_concentration: Record<string, number>;
  strategy_exposure: Record<string, number>;
  available_buying_power: number;
  max_concurrent_trades: number;
};

export default function PortfolioPanel({ portfolio }: { portfolio: PortfolioData | null }) {
  if (!portfolio) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading portfolio exposure...</div>;
  }

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Portfolio</h3>
        <span className="text-xs text-slate-300">Open: {portfolio.active_positions.length}</span>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-2 text-xs text-slate-300">
        <div className="rounded border border-terminal-line bg-black/20 p-2">Balance: {portfolio.account_balance.toFixed(2)}</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">Exposure: {portfolio.total_exposure.toFixed(2)}</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">Buying Power: {portfolio.available_buying_power.toFixed(2)}</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Risk: {(portfolio.risk_exposure_pct * 100).toFixed(1)}%
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Max Trades: {portfolio.max_concurrent_trades}
        </div>
      </div>

      <div className="mb-3 text-xs text-slate-300">
        <p className="mb-1 font-semibold text-slate-400">Allocation</p>
        {Object.keys(portfolio.sector_concentration).length === 0 && <p>No active sector allocation yet.</p>}
        {Object.entries(portfolio.sector_concentration).map(([sector, amount]) => (
          <p key={sector}>
            {sector}: {amount.toFixed(2)}
          </p>
        ))}
        {Object.entries(portfolio.strategy_exposure).map(([strategy, amount]) => (
          <p key={strategy}>
            {strategy}: {amount.toFixed(2)}
          </p>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Symbol</th>
              <th className="px-2 py-1">Side</th>
              <th className="px-2 py-1">Strategy</th>
              <th className="px-2 py-1">Units</th>
              <th className="px-2 py-1">Notional</th>
            </tr>
          </thead>
          <tbody>
            {portfolio.active_positions.slice(0, 6).map((pos, idx) => (
              <tr key={`${pos.symbol}-${idx}`} className="border-t border-terminal-line">
                <td className="px-2 py-1">{pos.symbol}</td>
                <td className="px-2 py-1">{pos.side}</td>
                <td className="px-2 py-1">{pos.strategy}</td>
                <td className="px-2 py-1">{pos.units.toFixed(2)}</td>
                <td className="px-2 py-1">{pos.notional.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
