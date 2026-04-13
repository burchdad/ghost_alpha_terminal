"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type CandleData = {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

type ChartDataPoint = {
  time: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  consensus?: number;
  signalType?: "BUY" | "SELL" | null;
};

type Props = {
  symbol: string;
  days?: number;
};

function CandleBody({ x, y, width, height, payload }: any) {
  if (!payload) return null;
  const { open, close, high, low } = payload;
  if (open === undefined || close === undefined) return null;

  const isGreen = close >= open;
  const color = isGreen ? "#10b981" : "#ef4444";
  
  // Scale: map price range to pixel height
  const range = high - low || 1;
  const scale = (height || 50) / range;
  const wickX = x + (width || 20) / 2;
  
  // Wick (high-low line)
  const wickY1 = y + ((high - high) * scale); // Top
  const wickY2 = y + ((low - high) * scale); // Bottom
  
  // Body (open-close)
  const bodyY = y + ((Math.max(open, close) - high) * scale);
  const bodyHeight = Math.abs((close - open) * scale) || 1;

  return (
    <g>
      <line x1={wickX} y1={wickY1} x2={wickX} y2={wickY2} stroke={color} strokeWidth={1} />
      <rect
        x={x + 2}
        y={bodyY}
        width={(width || 20) - 4}
        height={bodyHeight}
        fill={color}
        stroke={color}
        strokeWidth={1}
      />
    </g>
  );
}

export default function CandlestickChart({ symbol, days = 90 }: Props) {
  const [data, setData] = useState<ChartDataPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [consensusScore, setConsensusScore] = useState(0.5);

  useEffect(() => {
    if (!symbol) return;
    setLoading(true);
    
    Promise.all([
      fetch(`${API_BASE}/signal/history/${symbol}?days=${days}`),
      fetch(`${API_BASE}/swarm/${symbol}`),
    ])
      .then(async ([histRes, swarmRes]) => {
        const hist = histRes.ok ? await histRes.json() : { bars: [] };
        const swarm = swarmRes.ok ? await swarmRes.json() : { consensus_score: 0.5 };
        
        if (swarm?.consensus_score) {
          setConsensusScore(swarm.consensus_score);
        }
        
        const bars: CandleData[] = hist.bars || [];
        const chartData: ChartDataPoint[] = bars.map((bar) => ({
          time: new Date(bar.timestamp).toLocaleDateString(),
          open: bar.open,
          high: bar.high,
          low: bar.low,
          close: bar.close,
          volume: bar.volume,
          consensus: swarm?.consensus_score || 0.5,
        }));
        setData(chartData);
      })
      .finally(() => setLoading(false));
  }, [symbol, days]);

  return (
    <div className="w-full h-96 bg-slate-950 rounded-lg p-4 border border-slate-800">
      <div className="flex justify-between items-start mb-2">
        <h3 className="text-sm font-semibold text-slate-300">{symbol} Price Action</h3>
        <div className="text-xs text-slate-400">
          <span className="text-green-500 font-mono">Swarm Consensus: {(consensusScore * 100).toFixed(0)}%</span>
        </div>
      </div>

      {loading ? (
        <div className="h-full flex items-center justify-center text-slate-500">
          Loading candlesticks...
        </div>
      ) : data.length === 0 ? (
        <div className="h-full flex items-center justify-center text-slate-500">
          No data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 20 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
            <XAxis
              dataKey="time"
              tick={{ fontSize: 12 }}
              stroke="#64748b"
              interval={Math.floor(data.length / 6)}
            />
            <YAxis
              yAxisId="left"
              tick={{ fontSize: 12 }}
              stroke="#64748b"
              domain={["dataMin - 1", "dataMax + 1"]}
            />
            <YAxis
              yAxisId="right"
              orientation="right"
              tick={{ fontSize: 12 }}
              stroke="#64748b"
              domain={[0, 1]}
              label={{ value: "Swarm Confidence", angle: 90, position: "insideRight", offset: -10 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1e293b",
                border: "1px solid #475569",
                borderRadius: "4px",
              }}
              formatter={(value: any) => {
                if (typeof value === "number") return value.toFixed(2);
                return value;
              }}
            />
            <Legend wrapperStyle={{ paddingTop: "10px" }} />

            {/* Candlesticks as custom bars (simplified - one bar per candle) */}
            <Bar
              yAxisId="left"
              dataKey="close"
              fill="#94a3b8"
              shape={<CandleBody />}
              isAnimationActive={false}
            />

            {/* Consensus score overlay */}
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="consensus"
              stroke="#8b5cf6"
              strokeWidth={2}
              dot={false}
              name="Swarm Consensus"
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
