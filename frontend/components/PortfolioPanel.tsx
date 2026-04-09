"use client";

import { useState } from "react";

const POS_PAGE = 8;

type ActivePosition = {
  symbol: string;
  strategy: string;
  side: string;
  entry_price: number;
  current_price?: number;
  unrealized_pnl?: number;
  unrealized_pnl_pct?: number;
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
  broker_accounts?: {
    broker: string;
    account_label: string;
    account_mode: string;
    connected: boolean;
    account_balance: number | null;
    buying_power: number | null;
    currency: string;
    last_error: string | null;
  }[];
};

function pnlColor(pnl: number | undefined) {
  if (pnl === undefined || pnl === 0) return "text-slate-300";
  return pnl > 0 ? "text-terminal-bull" : "text-terminal-bear";
}

export default function PortfolioPanel({ portfolio }: { portfolio: PortfolioData | null }) {
  const [posPage, setPosPage] = useState(0);

  if (!portfolio) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading portfolio exposure...</div>;
  }

  const positions = portfolio.active_positions;
  const totalPages = Math.ceil(positions.length / POS_PAGE);
  const pagePositions = positions.slice(posPage * POS_PAGE, (posPage + 1) * POS_PAGE);

  const totalUnrealizedPnl = positions.reduce((sum, p) => sum + (p.unrealized_pnl ?? 0), 0);

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Portfolio</h3>
        <div className="flex items-center gap-3">
          {positions.length > 0 && (
            <span className={`text-xs font-semibold ${pnlColor(totalUnrealizedPnl)}`}>
              Unrealized: {totalUnrealizedPnl >= 0 ? "+" : ""}${totalUnrealizedPnl.toFixed(2)}
            </span>
          )}
          <span className="text-xs text-slate-300">Open: {positions.length}</span>
        </div>
      </div>

      <div className="mb-3 grid grid-cols-2 gap-2 text-xs text-slate-300">
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Balance: <span className="font-semibold text-slate-200">${portfolio.account_balance.toFixed(2)}</span>
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Exposure: ${portfolio.total_exposure.toFixed(2)}
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Buying Power: <span className="text-terminal-accent">${portfolio.available_buying_power.toFixed(2)}</span>
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Risk: {(portfolio.risk_exposure_pct * 100).toFixed(1)}%
        </div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">
          Max Trades: {portfolio.max_concurrent_trades}
        </div>
      </div>

      {portfolio.broker_accounts && portfolio.broker_accounts.length > 0 && (
        <div className="mb-3 text-xs text-slate-300">
          <p className="mb-1 font-semibold text-slate-400">Broker Accounts</p>
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            {portfolio.broker_accounts.map((acct) => (
              <div
                key={`${acct.broker}-${acct.account_mode}`}
                className="rounded border border-terminal-line bg-black/20 p-2"
              >
                <div className="mb-1 flex items-center justify-between">
                  <span className="font-semibold">{acct.account_label}</span>
                  <span className={acct.connected ? "text-emerald-300" : "text-amber-300"}>
                    {acct.connected ? "Connected" : "Unavailable"}
                  </span>
                </div>
                <p>Balance: {acct.account_balance != null ? `$${acct.account_balance.toFixed(2)}` : "N/A"}</p>
                <p>Buying Power: {acct.buying_power != null ? `$${acct.buying_power.toFixed(2)}` : "N/A"}</p>
                {acct.last_error ? (
                  <p className="mt-1 text-[11px] text-amber-300">{acct.last_error}</p>
                ) : null}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mb-3 text-xs text-slate-300">
        <p className="mb-1 font-semibold text-slate-400">Allocation</p>
        {Object.keys(portfolio.sector_concentration).length === 0 && <p>No active sector allocation yet.</p>}
        {Object.entries(portfolio.sector_concentration).map(([sector, amount]) => {
          const pct = portfolio.total_exposure > 0 ? ((amount / portfolio.total_exposure) * 100).toFixed(1) : "0.0";
          return (
            <p key={sector}>
              {sector}: ${amount.toFixed(0)} ({pct}%)
            </p>
          );
        })}
        {Object.entries(portfolio.strategy_exposure).map(([strategy, amount]) => {
          const pct = portfolio.total_exposure > 0 ? ((amount / portfolio.total_exposure) * 100).toFixed(1) : "0.0";
          return (
            <p key={strategy}>
              {strategy}: ${amount.toFixed(0)} ({pct}%)
            </p>
          );
        })}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Symbol</th>
              <th className="px-2 py-1">Side</th>
              <th className="px-2 py-1">Strategy</th>
              <th className="px-2 py-1">Entry $</th>
              <th className="px-2 py-1">Current $</th>
              <th className="px-2 py-1">Units</th>
              <th className="px-2 py-1">Notional</th>
              <th className="px-2 py-1">Unr. P&L</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 && (
              <tr>
                <td className="px-2 py-3 text-slate-400" colSpan={8}>
                  No open positions.
                </td>
              </tr>
            )}
            {pagePositions.map((pos, idx) => (
              <tr key={`${pos.symbol}-${idx}`} className="border-t border-terminal-line">
                <td className="px-2 py-1 font-semibold">{pos.symbol}</td>
                <td className="px-2 py-1">{pos.side}</td>
                <td className="px-2 py-1">{pos.strategy}</td>
                <td className="px-2 py-1">${pos.entry_price.toFixed(2)}</td>
                <td className="px-2 py-1">
                  {pos.current_price ? `$${pos.current_price.toFixed(2)}` : "—"}
                </td>
                <td className="px-2 py-1">{pos.units.toFixed(4)}</td>
                <td className="px-2 py-1">${pos.notional.toFixed(2)}</td>
                <td className={`px-2 py-1 font-semibold ${pnlColor(pos.unrealized_pnl)}`}>
                  {pos.unrealized_pnl !== undefined
                    ? `${pos.unrealized_pnl >= 0 ? "+" : ""}$${pos.unrealized_pnl.toFixed(2)}`
                    : "—"}
                  {pos.unrealized_pnl_pct !== undefined && pos.unrealized_pnl_pct !== 0 && (
                    <span className="ml-1 text-[10px] opacity-70">
                      ({(pos.unrealized_pnl_pct * 100).toFixed(2)}%)
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
          <span>
            Page {posPage + 1} / {totalPages}
          </span>
          <div className="flex gap-2">
            <button
              disabled={posPage === 0}
              onClick={() => setPosPage((p) => p - 1)}
              className="rounded border border-terminal-line px-2 py-1 disabled:opacity-40 hover:text-terminal-accent"
            >
              Prev
            </button>
            <button
              disabled={posPage >= totalPages - 1}
              onClick={() => setPosPage((p) => p + 1)}
              className="rounded border border-terminal-line px-2 py-1 disabled:opacity-40 hover:text-terminal-accent"
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
