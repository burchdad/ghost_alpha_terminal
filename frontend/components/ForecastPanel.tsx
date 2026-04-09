type Forecast = {
  direction: "UP" | "DOWN" | "SIDEWAYS";
  confidence: number;
  volatility: "LOW" | "MEDIUM" | "HIGH";
  range_bound: boolean;
};

type ExtendedForecast = Forecast & {
  symbol?: string;
  timeframe?: string;
  generated_at?: string;
  forecast_prices?: number[];
};

export default function ForecastPanel({ forecast }: { forecast: ExtendedForecast | null }) {
  if (!forecast) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading forecast...</div>;
  }

  const dirColor =
    forecast.direction === "UP" ? "text-terminal-bull" : forecast.direction === "DOWN" ? "text-terminal-bear" : "text-terminal-warn";

  const generatedAt = forecast.generated_at ? new Date(forecast.generated_at) : null;
  const ageMinutes = generatedAt ? Math.round((Date.now() - generatedAt.getTime()) / 60000) : null;
  const staleWarning = ageMinutes !== null && ageMinutes > 30;

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Kronos Forecast</h3>
        {forecast.symbol && (
          <span className="text-xs text-slate-400">
            {forecast.symbol} · {forecast.timeframe ?? "1d"}
          </span>
        )}
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <span className="text-slate-400">Direction</span>
        <span className={dirColor}>{forecast.direction}</span>
        <span className="text-slate-400">Confidence</span>
        <span>{Math.round(forecast.confidence * 100)}%</span>
        <span className="text-slate-400">Volatility</span>
        <span>{forecast.volatility}</span>
        <span className="text-slate-400">Range Bound</span>
        <span>{forecast.range_bound ? "Yes" : "No"}</span>
        {generatedAt && (
          <>
            <span className="text-slate-400">Generated</span>
            <span className={staleWarning ? "text-amber-300" : "text-slate-300"}>
              {ageMinutes !== null && ageMinutes < 60
                ? `${ageMinutes}m ago`
                : generatedAt.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              {staleWarning && " ⚠"}
            </span>
          </>
        )}
      </div>
      {forecast.forecast_prices && forecast.forecast_prices.length > 0 && (
        <div className="mt-3">
          <p className="mb-1 text-xs text-slate-400">10-Step Statistical Projection</p>
          <div className="flex items-end gap-1">
            {forecast.forecast_prices.map((price, i) => {
              const first = forecast.forecast_prices![0];
              const pctChange = ((price - first) / first) * 100;
              const barH = Math.min(40, Math.max(4, Math.abs(pctChange) * 8 + 4));
              return (
                <div key={i} className="flex flex-1 flex-col items-center gap-0.5">
                  <span className="text-[9px] text-slate-500">{pctChange >= 0 ? "+" : ""}{pctChange.toFixed(1)}%</span>
                  <div
                    style={{ height: `${barH}px` }}
                    className={`w-full rounded-sm ${pctChange >= 0 ? "bg-terminal-bull/50" : "bg-terminal-bear/50"}`}
                  />
                  <span className="text-[8px] text-slate-600">F{i + 1}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
