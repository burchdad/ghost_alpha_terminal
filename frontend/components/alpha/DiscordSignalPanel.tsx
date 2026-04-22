"use client";

import { useEffect, useState } from "react";

type OptionsSignal = {
  symbol: string;
  direction: "CALL" | "PUT";
  strike: number | null;
  expiry_raw: string | null;
};

type WatchlistEntry = {
  symbol: string;
  asset_class: string;
  source: string;
  note: string | null;
  pinned_by: string | null;
  pinned_at: string;
};

export type DiscordSignalStatus = {
  enabled: boolean;
  window_hours: number;
  active_symbols: string[];
  pinned_symbols: string[];
  options_signals: OptionsSignal[];
  source_counts: Record<string, number>;
  generated_at: string;
  config: {
    signal_channels: string[];
    confidence_boost: number;
    max_inject: number;
  };
};

type Props = {
  status: DiscordSignalStatus | null;
  watchlist: WatchlistEntry[];
  onPin: (symbol: string, assetClass: string, note: string) => Promise<void>;
  onUnpin: (symbol: string) => Promise<void>;
  onRefresh: () => Promise<void>;
};

export default function DiscordSignalPanel({ status, watchlist, onPin, onUnpin, onRefresh }: Props) {
  const [pinInput, setPinInput] = useState("");
  const [pinNote, setPinNote] = useState("");
  const [pinAssetClass, setPinAssetClass] = useState("equity");
  const [pinning, setPinning] = useState(false);
  const [unpinning, setUnpinning] = useState<string | null>(null);

  async function handlePin() {
    const sym = pinInput.trim().toUpperCase();
    if (!sym) return;
    setPinning(true);
    try {
      await onPin(sym, pinAssetClass, pinNote.trim());
      setPinInput("");
      setPinNote("");
    } finally {
      setPinning(false);
    }
  }

  async function handleUnpin(symbol: string) {
    setUnpinning(symbol);
    try {
      await onUnpin(symbol);
    } finally {
      setUnpinning(null);
    }
  }

  if (!status) {
    return (
      <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3 text-xs text-slate-400">
        Loading Discord signal status…
      </section>
    );
  }

  const allSymbols = Array.from(new Set([...status.active_symbols, ...status.pinned_symbols]));
  const optionsMap: Record<string, OptionsSignal[]> = {};
  for (const sig of status.options_signals) {
    if (!optionsMap[sig.symbol]) optionsMap[sig.symbol] = [];
    optionsMap[sig.symbol].push(sig);
  }

  return (
    <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3 space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-terminal-accent">
            Discord Signal Feed
          </h3>
          <span
            className={`rounded px-1.5 py-0.5 text-[9px] font-bold uppercase ${
              status.enabled
                ? "bg-emerald-900/60 text-emerald-400"
                : "bg-zinc-800 text-slate-500"
            }`}
          >
            {status.enabled ? "live" : "disabled"}
          </span>
        </div>
        <button
          onClick={onRefresh}
          className="text-[10px] text-slate-500 hover:text-slate-300 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Config summary */}
      <div className="grid grid-cols-3 gap-2 text-[10px] text-slate-500">
        <div>
          <span className="block text-slate-400 font-medium">Window</span>
          {status.window_hours}h
        </div>
        <div>
          <span className="block text-slate-400 font-medium">Boost</span>
          ×{status.config.confidence_boost.toFixed(2)}
        </div>
        <div>
          <span className="block text-slate-400 font-medium">Channels</span>
          {status.config.signal_channels.length === 0 ? "All" : status.config.signal_channels.length}
        </div>
      </div>

      {/* Active signals */}
      {allSymbols.length > 0 ? (
        <div>
          <p className="mb-1 text-[10px] text-slate-500 uppercase tracking-wider">Active Signals ({allSymbols.length})</p>
          <div className="flex flex-wrap gap-1">
            {allSymbols.map((sym) => {
              const isPinned = status.pinned_symbols.includes(sym);
              const isActive = status.active_symbols.includes(sym);
              const opts = optionsMap[sym];
              return (
                <span
                  key={sym}
                  title={opts ? opts.map((o) => `${o.direction}${o.strike ? ` $${o.strike}` : ""}${o.expiry_raw ? ` ${o.expiry_raw}` : ""}`).join(" · ") : undefined}
                  className={`rounded px-2 py-0.5 text-[10px] font-semibold cursor-default ${
                    opts
                      ? "bg-purple-900/60 text-purple-300"
                      : isPinned && isActive
                      ? "bg-terminal-accent/20 text-terminal-accent"
                      : isPinned
                      ? "bg-blue-900/40 text-blue-300"
                      : "bg-slate-700/40 text-slate-300"
                  }`}
                >
                  {sym}
                  {opts ? (
                    <span className="ml-1 text-[9px]">
                      {opts.some((o) => o.direction === "CALL") ? "C" : ""}
                      {opts.some((o) => o.direction === "PUT") ? "P" : ""}
                    </span>
                  ) : null}
                </span>
              );
            })}
          </div>
        </div>
      ) : (
        <p className="text-[10px] text-slate-600 italic">
          {status.enabled ? "No active Discord signals in window." : "Enable DISCORD_INBOUND_ENABLED to start receiving signals."}
        </p>
      )}

      {/* Options signals detail */}
      {status.options_signals.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] text-slate-500 uppercase tracking-wider">Options Signals</p>
          <div className="space-y-1">
            {status.options_signals.slice(0, 10).map((sig, i) => (
              <div key={i} className="flex items-center gap-2 text-[10px] rounded bg-purple-900/20 px-2 py-1">
                <span className="font-bold text-slate-200">{sig.symbol}</span>
                <span className={`font-semibold ${sig.direction === "CALL" ? "text-emerald-400" : "text-red-400"}`}>
                  {sig.direction}
                </span>
                {sig.strike && <span className="text-slate-400">${sig.strike}</span>}
                {sig.expiry_raw && <span className="text-slate-500">{sig.expiry_raw}</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pinned watchlist */}
      {watchlist.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] text-slate-500 uppercase tracking-wider">Pinned Watchlist ({watchlist.length})</p>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {watchlist.map((entry) => (
              <div
                key={entry.symbol}
                className="flex items-center justify-between gap-2 rounded bg-black/20 px-2 py-1 text-[10px]"
              >
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-200">{entry.symbol}</span>
                  <span className="text-slate-600">{entry.asset_class}</span>
                  {entry.note && <span className="text-slate-500 italic truncate max-w-[80px]">{entry.note}</span>}
                  <span className={`text-[9px] rounded px-1 ${entry.source === "manual" ? "bg-blue-900/40 text-blue-400" : "bg-emerald-900/40 text-emerald-400"}`}>
                    {entry.source}
                  </span>
                </div>
                <button
                  onClick={() => handleUnpin(entry.symbol)}
                  disabled={unpinning === entry.symbol}
                  className="text-[9px] text-red-500 hover:text-red-400 disabled:opacity-50 transition-colors"
                >
                  {unpinning === entry.symbol ? "…" : "Unpin"}
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pin new symbol */}
      <div className="border-t border-terminal-line pt-2">
        <p className="mb-1.5 text-[10px] text-slate-500 uppercase tracking-wider">Pin Symbol</p>
        <div className="flex gap-1.5 flex-wrap">
          <input
            type="text"
            placeholder="TICKER"
            value={pinInput}
            maxLength={6}
            onChange={(e) => setPinInput(e.target.value.toUpperCase())}
            className="w-20 rounded border border-terminal-line bg-black/40 px-2 py-1 text-[11px] text-slate-200 uppercase"
          />
          <select
            value={pinAssetClass}
            onChange={(e) => setPinAssetClass(e.target.value)}
            className="rounded border border-terminal-line bg-black/40 px-2 py-1 text-[11px] text-slate-300"
          >
            <option value="equity">Equity</option>
            <option value="crypto">Crypto</option>
            <option value="etf">ETF</option>
            <option value="option">Option</option>
          </select>
          <input
            type="text"
            placeholder="Note (optional)"
            value={pinNote}
            maxLength={120}
            onChange={(e) => setPinNote(e.target.value)}
            className="flex-1 min-w-[80px] rounded border border-terminal-line bg-black/40 px-2 py-1 text-[11px] text-slate-300"
          />
          <button
            onClick={handlePin}
            disabled={pinning || !pinInput.trim()}
            className="rounded bg-terminal-accent/20 border border-terminal-accent/40 px-3 py-1 text-[11px] font-semibold text-terminal-accent hover:bg-terminal-accent/30 disabled:opacity-50 transition-colors"
          >
            {pinning ? "Pinning…" : "Pin"}
          </button>
        </div>
      </div>
    </section>
  );
}
