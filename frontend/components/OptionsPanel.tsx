"use client";

import { useEffect, useState } from "react";

import { apiFetch } from "../lib/apiClient";
import { ensureHighTrust } from "../lib/highTrust";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type Contract = {
  option_symbol?: string | null;
  strike: number;
  expiration?: string;
  option_type: "CALL" | "PUT";
  iv: number;
  open_interest: number;
  volume: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
  bid?: number | null;
  ask?: number | null;
  mid?: number | null;
  last?: number | null;
  source?: "tradier" | "synthetic";
};

type OptionsData = {
  symbol?: string;
  source?: "tradier" | "synthetic";
  selected_expiration?: string | null;
  available_expirations?: string[];
  avg_iv: number;
  underlying_price?: number;
  contracts: Contract[];
};

type StrategyLeg = {
  instrument: "option" | "equity";
  action: string;
  ratio: number;
  quantity: number;
  shares?: number | null;
  option_symbol?: string | null;
  option_type?: "CALL" | "PUT" | null;
  strike?: number | null;
  expiration?: string | null;
  bid?: number | null;
  ask?: number | null;
  mid?: number | null;
  estimated_leg_value?: number | null;
};

type StrategyResult = {
  approved: boolean;
  strategy?: string | null;
  order_class?: "option" | "multileg" | "combo" | null;
  order_preview: boolean;
  estimated_net_debit?: number | null;
  estimated_net_credit?: number | null;
  reason: string;
  warnings: string[];
  legs: StrategyLeg[];
  risk?: {
    risk_level: "LOW" | "MEDIUM" | "HIGH";
    max_loss_amount: number;
    spread_pct: number;
  } | null;
};

type StrategyBias = "BULLISH" | "BEARISH" | "NEUTRAL";

export default function OptionsPanel({
  options,
  symbol,
  onStrategyExecuted,
}: {
  options: OptionsData | null;
  symbol: string;
  onStrategyExecuted?: () => void;
}) {
  const [supportedStrategies, setSupportedStrategies] = useState<string[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState("LONG_CALL");
  const [bias, setBias] = useState<StrategyBias>("BULLISH");
  const [quantity, setQuantity] = useState(1);
  const [working, setWorking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<StrategyResult | null>(null);

  useEffect(() => {
    async function loadSupported() {
      try {
        const response = await apiFetch(`${API_BASE}/options/strategies/supported`, { apiBase: API_BASE });
        if (!response.ok) {
          return;
        }
        const strategies = (await response.json()) as string[];
        setSupportedStrategies(strategies);
        if (strategies.length > 0 && !strategies.includes(selectedStrategy)) {
          setSelectedStrategy(strategies[0]);
        }
      } catch {
        // Keep default static selection if endpoint is unavailable.
      }
    }
    void loadSupported();
  }, [selectedStrategy]);

  useEffect(() => {
    if (selectedStrategy.includes("PUT")) {
      if (selectedStrategy.startsWith("LONG") || selectedStrategy.startsWith("PROTECTIVE")) {
        setBias("BEARISH");
      }
    } else if (selectedStrategy.includes("CALL") && selectedStrategy.startsWith("LONG")) {
      setBias("BULLISH");
    } else if (selectedStrategy.includes("STRADDLE") || selectedStrategy.includes("STRANGLE") || selectedStrategy.includes("CONDOR") || selectedStrategy.includes("BUTTERFLY")) {
      setBias("NEUTRAL");
    }
  }, [selectedStrategy]);

  async function runStrategy(preview: boolean) {
    if (!symbol) {
      return;
    }
    setWorking(true);
    setError(null);
    try {
      const trusted = await ensureHighTrust({ apiBase: API_BASE });
      if (!trusted) {
        setError("Security verification was cancelled.");
        return;
      }

      const response = await apiFetch(`${API_BASE}/options/execute`, {
        apiBase: API_BASE,
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          symbol,
          strategy: selectedStrategy,
          bias,
          quantity,
          preview,
          confidence: 0.66,
        }),
      });

      if (!response.ok) {
        const payload = (await response.json().catch(() => null)) as { detail?: string } | null;
        setError(payload?.detail ?? `Request failed (${response.status})`);
        return;
      }

      const payload = (await response.json()) as StrategyResult;
      setResult(payload);
      if (!preview && payload.approved && onStrategyExecuted) {
        onStrategyExecuted();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to run strategy action");
    } finally {
      setWorking(false);
    }
  }

  if (!options) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading options chain...</div>;
  }

  const top = options.contracts.slice(0, 10);
  const strategies = supportedStrategies.length > 0
    ? supportedStrategies
    : [
        "LONG_CALL",
        "LONG_PUT",
        "VERTICAL_CALL",
        "VERTICAL_PUT",
        "IRON_CONDOR",
        "STRADDLE",
        "STRANGLE",
        "COVERED_CALL",
      ];

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Options Chain (Top 10)</h3>
        <span className="text-xs text-slate-300">
          Avg IV: {options.avg_iv.toFixed(2)}% {options.source ? `| ${options.source}` : ""}
        </span>
      </div>

      <div className="mb-3 rounded border border-terminal-line bg-black/20 p-3 text-xs text-slate-300">
        <div className="mb-2 grid grid-cols-1 gap-2 md:grid-cols-4">
          <select
            value={selectedStrategy}
            onChange={(event) => setSelectedStrategy(event.target.value)}
            className="rounded border border-terminal-line bg-black/30 px-2 py-1 text-xs text-slate-200"
          >
            {strategies.map((strategy) => (
              <option key={strategy} value={strategy}>
                {strategy}
              </option>
            ))}
          </select>

          <select
            value={bias}
            onChange={(event) => setBias(event.target.value as StrategyBias)}
            className="rounded border border-terminal-line bg-black/30 px-2 py-1 text-xs text-slate-200"
          >
            <option value="BULLISH">BULLISH</option>
            <option value="BEARISH">BEARISH</option>
            <option value="NEUTRAL">NEUTRAL</option>
          </select>

          <input
            type="number"
            min={1}
            max={100}
            value={quantity}
            onChange={(event) => setQuantity(Math.max(1, Math.min(100, Number(event.target.value) || 1)))}
            className="rounded border border-terminal-line bg-black/30 px-2 py-1 text-xs text-slate-200"
          />

          <div className="flex gap-2">
            <button
              type="button"
              disabled={working}
              onClick={() => void runStrategy(true)}
              className="rounded border border-terminal-accent/50 px-2 py-1 text-[11px] text-terminal-accent hover:bg-terminal-accent/10 disabled:opacity-60"
            >
              {working ? "..." : "Preview"}
            </button>
            <button
              type="button"
              disabled={working}
              onClick={() => void runStrategy(false)}
              className="rounded border border-emerald-500/60 px-2 py-1 text-[11px] text-emerald-300 hover:bg-emerald-500/10 disabled:opacity-60"
            >
              Execute
            </button>
          </div>
        </div>
        <div className="text-[11px] text-slate-400">
          Symbol {symbol} | Underlying {options.underlying_price?.toFixed(2)} | Expiry {options.selected_expiration ?? "auto"}
        </div>
        {error ? <div className="mt-2 text-[11px] text-rose-300">{error}</div> : null}
      </div>

      {result ? (
        <div className="mb-3 rounded border border-terminal-line bg-black/20 p-3 text-xs text-slate-300">
          <div className="mb-1 flex items-center justify-between">
            <span className={result.approved ? "text-emerald-300" : "text-rose-300"}>
              {result.order_preview ? "Preview" : "Execution"}: {result.approved ? "Approved" : "Blocked"}
            </span>
            <span>{result.strategy} | {result.order_class}</span>
          </div>
          <div className="mb-1 text-[11px] text-slate-400">{result.reason}</div>
          <div className="mb-1 text-[11px] text-slate-400">
            Debit {result.estimated_net_debit?.toFixed(2) ?? "-"} | Credit {result.estimated_net_credit?.toFixed(2) ?? "-"}
          </div>
          {result.risk ? (
            <div className="mb-1 text-[11px] text-slate-400">
              Risk {result.risk.risk_level} | Max Loss {result.risk.max_loss_amount.toFixed(2)} | Spread {(result.risk.spread_pct * 100).toFixed(1)}%
            </div>
          ) : null}
          {result.warnings.length > 0 ? (
            <ul className="mt-1 list-disc pl-4 text-[11px] text-amber-300">
              {result.warnings.slice(0, 3).map((warning, idx) => (
                <li key={`warn-${idx}`}>{warning}</li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Type</th>
              <th className="px-2 py-1">Strike</th>
              <th className="px-2 py-1">Bid</th>
              <th className="px-2 py-1">Ask</th>
              <th className="px-2 py-1">IV</th>
              <th className="px-2 py-1">OI</th>
              <th className="px-2 py-1">Vol</th>
              <th className="px-2 py-1">Delta</th>
              <th className="px-2 py-1">Gamma</th>
              <th className="px-2 py-1">Theta</th>
              <th className="px-2 py-1">Vega</th>
            </tr>
          </thead>
          <tbody>
            {top.map((c, i) => (
              <tr key={`${c.option_type}-${c.strike}-${i}`} className="border-t border-terminal-line">
                <td className="px-2 py-1">{c.option_type}</td>
                <td className="px-2 py-1">{c.strike}</td>
                <td className="px-2 py-1">{c.bid?.toFixed(2) ?? "-"}</td>
                <td className="px-2 py-1">{c.ask?.toFixed(2) ?? "-"}</td>
                <td className="px-2 py-1">{c.iv}%</td>
                <td className="px-2 py-1">{c.open_interest}</td>
                <td className="px-2 py-1">{c.volume}</td>
                <td className="px-2 py-1">{c.delta}</td>
                <td className="px-2 py-1">{c.gamma}</td>
                <td className="px-2 py-1">{c.theta}</td>
                <td className="px-2 py-1">{c.vega}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
