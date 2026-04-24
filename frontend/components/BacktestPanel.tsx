"use client";

import { useCallback, useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiFetch } from "../lib/apiClient";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";
const PAGE_SIZE = 10;

type EquityPoint = { timestamp: string; equity: number };
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
type BacktestResult = {
  total_trades: number;
  win_rate: number;
  total_pnl: number;
  max_drawdown: number;
  sharpe_ratio: number;
  equity_curve: EquityPoint[];
  trade_history: TradeRow[];
};
type Params = {
  timeframe: string;
  lookbackDays: number;
  takeProfitPct: number;
  stopLossPct: number;
  maxHoldPeriods: number;
};

const DEFAULT_PARAMS: Params = {
  timeframe: "1d",
  lookbackDays: 180,
  takeProfitPct: 5,
  stopLossPct: 2,
  maxHoldPeriods: 5,
};

function fmtDate(iso: string): string {
  try {
    const d = new Date(iso);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  } catch {
    return iso;
  }
}

export default function BacktestPanel({ symbol }: { symbol: string }) {
  const [params, setParams] = useState<Params>(DEFAULT_PARAMS);
  const [draft, setDraft] = useState<Params>(DEFAULT_PARAMS);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [showParams, setShowParams] = useState(false);

  const runBacktest = useCallback(
    async (p: Params) => {
      setLoading(true);
      setError(null);
      try {
        const end = new Date();
        const start = new Date();
        start.setDate(end.getDate() - p.lookbackDays);
        const res = await apiFetch(`${API_BASE}/backtest`, {
          apiBase: API_BASE,
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            symbol,
            timeframe: p.timeframe,
            start_date: start.toISOString(),
            end_date: end.toISOString(),
            take_profit_pct: p.takeProfitPct / 100,
            stop_loss_pct: p.stopLossPct / 100,
            max_hold_periods: p.maxHoldPeriods,
          }),
        });
        if (!res.ok) {
          setError(`Backtest unavailable (${res.status}). Try again in a moment.`);
          return;
        }
        const data = (await res.json()) as BacktestResult;
        setResult(data);
        setPage(0);
      } catch {
        setError("Backtest request failed. Check backend connectivity and retry.");
      } finally {
        setLoading(false);
      }
    },
    [symbol],
  );

  useEffect(() => {
    void runBacktest(DEFAULT_PARAMS);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [symbol]);

  function applyParams() {
    setParams(draft);
    setShowParams(false);
    void runBacktest(draft);
  }

  const chartData = (result?.equity_curve ?? []).map((pt) => ({
    date: fmtDate(pt.timestamp),
    equity: pt.equity,
  }));

  const totalPages = Math.ceil((result?.trade_history.length ?? 0) / PAGE_SIZE);
  const pageTrades = (result?.trade_history ?? []).slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-terminal-accent">Backtest & Simulation</h3>
        <div className="flex items-center gap-2">
          {result && (
            <span className="text-xs text-slate-300">
              {result.total_trades} trades · {params.lookbackDays}d lookback
            </span>
          )}
          <button
            onClick={() => setShowParams((v) => !v)}
            className="rounded border border-terminal-line px-2 py-1 text-xs text-terminal-accent hover:bg-terminal-accent/10"
          >
            {showParams ? "Hide" : "Configure"}
          </button>
          <button
            onClick={() => void runBacktest(params)}
            disabled={loading}
            className="rounded border border-terminal-accent bg-terminal-accent/10 px-2 py-1 text-xs text-terminal-accent disabled:opacity-50"
          >
            {loading ? "Running…" : "Re-run"}
          </button>
        </div>
      </div>

      {showParams && (
        <div className="mb-4 grid grid-cols-2 gap-3 rounded border border-terminal-line bg-black/20 p-3 text-xs md:grid-cols-5">
          <label className="flex flex-col gap-1">
            <span className="text-slate-400">Timeframe</span>
            <select
              value={draft.timeframe}
              onChange={(e) => setDraft((d) => ({ ...d, timeframe: e.target.value }))}
              className="rounded border border-terminal-line bg-black/40 px-1 py-1 text-xs text-slate-200"
            >
              {["1d", "1h", "4h"].map((tf) => (
                <option key={tf} value={tf}>
                  {tf}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-slate-400">Lookback (days)</span>
            <input
              type="number"
              min={30}
              max={365}
              value={draft.lookbackDays}
              onChange={(e) => setDraft((d) => ({ ...d, lookbackDays: Number(e.target.value) }))}
              className="rounded border border-terminal-line bg-black/40 px-2 py-1 text-xs text-slate-200"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-slate-400">Take Profit %</span>
            <input
              type="number"
              min={1}
              max={50}
              step={0.5}
              value={draft.takeProfitPct}
              onChange={(e) => setDraft((d) => ({ ...d, takeProfitPct: Number(e.target.value) }))}
              className="rounded border border-terminal-line bg-black/40 px-2 py-1 text-xs text-slate-200"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-slate-400">Stop Loss %</span>
            <input
              type="number"
              min={0.5}
              max={30}
              step={0.5}
              value={draft.stopLossPct}
              onChange={(e) => setDraft((d) => ({ ...d, stopLossPct: Number(e.target.value) }))}
              className="rounded border border-terminal-line bg-black/40 px-2 py-1 text-xs text-slate-200"
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-slate-400">Max Hold Periods</span>
            <input
              type="number"
              min={1}
              max={50}
              value={draft.maxHoldPeriods}
              onChange={(e) => setDraft((d) => ({ ...d, maxHoldPeriods: Number(e.target.value) }))}
              className="rounded border border-terminal-line bg-black/40 px-2 py-1 text-xs text-slate-200"
            />
          </label>
          <div className="col-span-2 flex items-end md:col-span-5">
            <button
              onClick={applyParams}
              className="rounded border border-terminal-bull bg-terminal-bull/10 px-3 py-1 text-xs text-terminal-bull"
            >
              Apply & Run
            </button>
          </div>
        </div>
      )}

      {loading && <div className="py-10 text-center text-xs text-slate-400">Running backtest simulation…</div>}

      {!loading && error && (
        <div className="mb-3 rounded border border-amber-500/40 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span>{error}</span>
            <button
              type="button"
              onClick={() => void runBacktest(params)}
              className="rounded border border-amber-500/50 px-2 py-1 hover:bg-amber-500/20"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {!loading && result && (
        <>
          <div className="mb-4 grid grid-cols-2 gap-2 text-xs text-slate-300 md:grid-cols-5">
            <div className="rounded border border-terminal-line bg-black/20 p-2">
              Win: <span className="text-terminal-bull">{(result.win_rate * 100).toFixed(1)}%</span>
            </div>
            <div className="rounded border border-terminal-line bg-black/20 p-2">
              PnL:{" "}
              <span className={result.total_pnl >= 0 ? "text-terminal-bull" : "text-terminal-bear"}>
                ${result.total_pnl.toFixed(0)}
              </span>
            </div>
            <div className="rounded border border-terminal-line bg-black/20 p-2">MDD: ${result.max_drawdown.toFixed(0)}</div>
            <div className="rounded border border-terminal-line bg-black/20 p-2">Sharpe: {result.sharpe_ratio.toFixed(2)}</div>
            <div className="rounded border border-terminal-line bg-black/20 p-2">Signals: {result.trade_history.length}</div>
          </div>

          <div className="mb-4 h-44 rounded border border-terminal-line bg-black/20 p-2">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid stroke="#103344" strokeDasharray="3 3" />
                <XAxis dataKey="date" stroke="#8db3c7" minTickGap={20} tick={{ fontSize: 9 }} />
                <YAxis stroke="#8db3c7" domain={["auto", "auto"]} tick={{ fontSize: 9 }} width={55} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0d232e", borderColor: "#103344" }}
                  formatter={(v: number) => [`$${v.toFixed(0)}`, "Equity"]}
                />
                <Line type="monotone" dataKey="equity" stroke="#22d3ee" dot={false} strokeWidth={2} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <div className="overflow-x-auto">
            <table className="min-w-full text-left text-xs">
              <thead className="text-slate-400">
                <tr>
                  <th className="px-2 py-1">Entry</th>
                  <th className="px-2 py-1">Exit</th>
                  <th className="px-2 py-1">Side</th>
                  <th className="px-2 py-1">Strategy</th>
                  <th className="px-2 py-1">Entry $</th>
                  <th className="px-2 py-1">Exit $</th>
                  <th className="px-2 py-1">PnL</th>
                  <th className="px-2 py-1">Ret%</th>
                  <th className="px-2 py-1">Result</th>
                </tr>
              </thead>
              <tbody>
                {pageTrades.map((trade, idx) => (
                  <tr
                    key={`${trade.entry_time}-${idx}`}
                    className={`border-t border-terminal-line ${trade.outcome === "WIN" ? "bg-terminal-bull/5" : "bg-terminal-bear/5"}`}
                  >
                    <td className="px-2 py-1 text-slate-400">{fmtDate(trade.entry_time)}</td>
                    <td className="px-2 py-1 text-slate-400">{fmtDate(trade.exit_time)}</td>
                    <td className="px-2 py-1">{trade.side}</td>
                    <td className="px-2 py-1">{trade.strategy}</td>
                    <td className="px-2 py-1">{trade.entry_price.toFixed(2)}</td>
                    <td className="px-2 py-1">{trade.exit_price.toFixed(2)}</td>
                    <td
                      className={`px-2 py-1 font-semibold ${trade.pnl >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}
                    >
                      {trade.pnl >= 0 ? "+" : ""}
                      {trade.pnl.toFixed(2)}
                    </td>
                    <td className="px-2 py-1">{(trade.return_pct * 100).toFixed(2)}%</td>
                    <td
                      className={`px-2 py-1 font-semibold ${trade.outcome === "WIN" ? "text-terminal-bull" : "text-terminal-bear"}`}
                    >
                      {trade.outcome}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className="mt-2 flex items-center justify-between text-xs text-slate-400">
              <span>
                Page {page + 1} / {totalPages}
              </span>
              <div className="flex gap-2">
                <button
                  disabled={page === 0}
                  onClick={() => setPage((p) => p - 1)}
                  className="rounded border border-terminal-line px-2 py-1 disabled:opacity-40 hover:text-terminal-accent"
                >
                  Prev
                </button>
                <button
                  disabled={page >= totalPages - 1}
                  onClick={() => setPage((p) => p + 1)}
                  className="rounded border border-terminal-line px-2 py-1 disabled:opacity-40 hover:text-terminal-accent"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
