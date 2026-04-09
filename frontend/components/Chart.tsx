"use client";

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

type ChartPoint = {
  name: string;
  price: number;
  forecast?: number;
};

type Props = {
  symbol: string;
  currentPrice: number;
  forecastPrices: number[];
};

export default function Chart({ symbol, currentPrice, forecastPrices }: Props) {
  const history: ChartPoint[] = Array.from({ length: 25 }).map((_, i) => ({
    name: `T-${24 - i}`,
    price: Number((currentPrice * (1 + Math.sin(i / 5) * 0.015)).toFixed(2)),
  }));

  const projected: ChartPoint[] = forecastPrices.map((value, i) => ({
    name: `F+${i + 1}`,
    price: history[history.length - 1]?.price ?? currentPrice,
    forecast: value,
  }));

  const data = [...history, ...projected];

  return (
    <div className="panel h-[340px] w-full rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">{symbol} Price + AI Projection</h3>
      </div>
      <ResponsiveContainer width="100%" height="90%">
        <LineChart data={data}>
          <CartesianGrid stroke="#103344" strokeDasharray="4 4" />
          <XAxis dataKey="name" stroke="#8db3c7" minTickGap={16} />
          <YAxis stroke="#8db3c7" domain={["auto", "auto"]} />
          <Tooltip contentStyle={{ backgroundColor: "#0d232e", borderColor: "#103344" }} />
          <Legend />
          <Line type="monotone" dataKey="price" stroke="#22d3ee" strokeWidth={2} dot={false} />
          <Line
            type="monotone"
            dataKey="forecast"
            stroke="#f59e0b"
            strokeWidth={2}
            dot={false}
            strokeDasharray="6 4"
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
