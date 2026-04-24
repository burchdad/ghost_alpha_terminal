"use client";

"use client";

import { useEffect, useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiFetch } from "../lib/apiClient";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type PriceBar = {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type ChartPoint = {
  name: string;
  price?: number;
  forecast?: number;
};

type Props = {
  symbol: string;
  forecastPrices: number[];
};

function formatBarDate(iso: string): string {
  try {
    const d = new Date(iso);
    return `${d.getMonth() + 1}/${d.getDate()}`;
  } catch {
    return iso;
  }
}

export default function Chart({ symbol, forecastPrices }: Props) {
  const [bars, setBars] = useState<PriceBar[]>([]);
  const [loading, setLoading] = useState(false);
  const [source, setSource] = useState<string>("alpaca");

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    apiFetch(`${API_BASE}/signal/history/${symbol}?days=90`, { apiBase: API_BASE })
      .then((r) => r.ok ? r.json() : null)
      .then((data: { bars?: PriceBar[]; source?: string } | null) => {
        if (data?.bars?.length) {
          setBars(data.bars);
          setSource(data.source ?? "alpaca");
        } else {
          setBars([]);
        }
      })
      .catch(() => setBars([]))
      .finally(() => setLoading(false));
  }, [symbol]);

  const data = useMemo<ChartPoint[]>(() => {
    const history: ChartPoint[] = bars.map((b) => ({
      name: formatBarDate(b.timestamp),
      price: b.close,
    }));

    const lastClose = bars.length > 0 ? bars[bars.length - 1].close : null;
    const projected: ChartPoint[] = forecastPrices.map((value, i) => ({
      name: `F+${i + 1}`,
      price: i === 0 ? lastClose ?? undefined : undefined,
      forecast: value,
    }));

    return [...history, ...projected];
  }, [bars, forecastPrices]);

  return (
    <div className="panel h-[340px] w-full rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">
          {symbol} Price History + Statistical Projection
        </h3>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          {loading && <span>Loading...</span>}
          {!loading && bars.length > 0 && (
            <span>{bars.length}d • {source}</span>
          )}
          {!loading && bars.length === 0 && <span className="text-amber-300">No price data</span>}
        </div>
      </div>
      <ResponsiveContainer width="100%" height="88%">
        <LineChart data={data}>
          <CartesianGrid stroke="#103344" strokeDasharray="4 4" />
          <XAxis dataKey="name" stroke="#8db3c7" minTickGap={20} tick={{ fontSize: 10 }} />
          <YAxis stroke="#8db3c7" domain={["auto", "auto"]} tick={{ fontSize: 10 }} width={55} />
          <Tooltip
            contentStyle={{ backgroundColor: "#0d232e", borderColor: "#103344" }}
            formatter={(val: number, name: string) => [
              `$${val.toFixed(2)}`,
              name === "price" ? "Close" : "Projection",
            ]}
          />
          <Legend />
          <Line
            type="monotone"
            dataKey="price"
            name="Close"
            stroke="#22d3ee"
            strokeWidth={2}
            dot={false}
            connectNulls={false}
          />
          <Line
            type="monotone"
            dataKey="forecast"
            name="Projection"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            strokeDasharray="6 4"
            connectNulls
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
