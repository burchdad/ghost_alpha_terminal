type Contract = {
  strike: number;
  option_type: "CALL" | "PUT";
  iv: number;
  open_interest: number;
  volume: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
};

type OptionsData = {
  avg_iv: number;
  contracts: Contract[];
};

export default function OptionsPanel({ options }: { options: OptionsData | null }) {
  if (!options) {
    return <div className="panel rounded-xl p-4 text-sm text-slate-300">Loading options chain...</div>;
  }

  const top = options.contracts.slice(0, 10);

  return (
    <div className="panel animate-riseIn rounded-xl p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-terminal-accent">Options Chain (Top 10)</h3>
        <span className="text-xs text-slate-300">Avg IV: {options.avg_iv.toFixed(2)}%</span>
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-xs">
          <thead className="text-slate-400">
            <tr>
              <th className="px-2 py-1">Type</th>
              <th className="px-2 py-1">Strike</th>
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
