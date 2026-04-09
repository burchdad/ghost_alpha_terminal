"use client";

import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type EquityPoint = {
  timestamp: string;
  equity: number;
};

type TradeRow = {
  entry_time: string;
  exit_time: string;
  side: "LONG" | "SHORT";
  strategy: string;
  entry_price: number;
  exit_price: number;
  pnl: number;
  return_pct: number;
  outcome: "WIN" | "LOSS";
};

type BacktestData = {
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  max_drawdown: number;
  sharpe_ratio: number;
  equity_curve: EquityPoint[];
  trade_history: TradeRow[];
};

export default function BacktestPanel({ backtest }: { backtest: BacktestData | null }) {
  if (!backtest) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Running backtest simulation...</div>;
  }

  const topTrades = backtest.trade_history.slice(0, 8);
  const chartData = backtest.equity_curve.map((point, idx) => ({ x: idx + 1, equity: point.equity }));

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Backtest & Simulation</h3>
        <span className="text-xs text-slate-300">Trades: {backtest.total_trades}</span>
      </div>

      <div className="mb-4 grid grid-cols-2 gap-2 text-xs text-slate-300 md:grid-cols-5">
        <div className="rounded border border-terminal-line bg-black/20 p-2">Win: {(backtest.win_rate * 100).toFixed(1)}%</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">PnL: {backtest.total_pnl.toFixed(2)}</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">MDD: {backtest.max_drawdown.toFixed(2)}</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">Sharpe: {backtest.sharpe_ratio.toFixed(2)}</div>
        <div className="rounded border border-terminal-line bg-black/20 p-2">Signals: {backtest.trade_history.length}</div>
      </div>

      <div className="mb-4 h-44 rounded border border-terminal-line bg-black/20 p-2">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData}>
            <XAxis dataKey="x" stroke="#8db3c7" />
            <YAxis stroke="#8db3c7" domain={["auto", "auto"]} />
            <Tooltip contentStyle={{ backgroundColor: "#0d232e", borderColor: "#103344" }} />
            <Line type="monotone" dataKey="equity" stroke="#22d3ee" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Side</th>
              <th className="px-2 py-1">Strategy</th>
              <th className="px-2 py-1">Entry</th>
              <th className="px-2 py-1">Exit</th>
              <th className="px-2 py-1">PnL</th>
              <th className="px-2 py-1">Outcome</th>
            </tr>
          </thead>
          <tbody>
            {topTrades.map((trade, idx) => (
              <tr key={`${trade.entry_time}-${idx}`} className="border-t border-terminal-line">
                <td className="px-2 py-1">{trade.side}</td>
                <td className="px-2 py-1">{trade.strategy}</td>
                <td className="px-2 py-1">{trade.entry_price.toFixed(2)}</td>
                <td className="px-2 py-1">{trade.exit_price.toFixed(2)}</td>
                <td className="px-2 py-1">{trade.pnl.toFixed(2)}</td>
                <td className="px-2 py-1">{trade.outcome}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
