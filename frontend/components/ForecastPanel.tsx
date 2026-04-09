type Forecast = {
  direction: "UP" | "DOWN" | "SIDEWAYS";
  confidence: number;
  volatility: "LOW" | "MEDIUM" | "HIGH";
  range_bound: boolean;
};

export default function ForecastPanel({ forecast }: { forecast: Forecast | null }) {
  if (!forecast) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading forecast...</div>;
  }

  const dirColor =
    forecast.direction === "UP" ? "text-terminal-bull" : forecast.direction === "DOWN" ? "text-terminal-bear" : "text-terminal-warn";

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <h3 className="mb-3 text-sm font-semibold text-terminal-accent">Kronos Forecast</h3>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <span className="text-slate-400">Direction</span>
        <span className={dirColor}>{forecast.direction}</span>
        <span className="text-slate-400">Confidence</span>
        <span>{Math.round(forecast.confidence * 100)}%</span>
        <span className="text-slate-400">Volatility</span>
        <span>{forecast.volatility}</span>
        <span className="text-slate-400">Range Bound</span>
        <span>{forecast.range_bound ? "Yes" : "No"}</span>
      </div>
    </div>
  );
}
