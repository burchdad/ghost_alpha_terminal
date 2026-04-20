type Props = {
  runtimePhaseLabel: string;
  brokerConnectedCount: number;
  executionReadyCount: number;
  automationOn: boolean;
  scanAgeSeconds: number | null;
  selectedBrokerLabel: string | null;
};

export default function RuntimeSummaryStrip({
  runtimePhaseLabel,
  brokerConnectedCount,
  executionReadyCount,
  automationOn,
  scanAgeSeconds,
  selectedBrokerLabel,
}: Props) {
  return (
    <section className="mb-4 rounded-xl border border-terminal-line bg-[#061723e6] p-3 backdrop-blur">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-terminal-accent">Runtime Summary</h2>
        <p className="text-[11px] text-slate-400">Fast-read operator strip</p>
      </div>
      <div className="grid grid-cols-2 gap-2 text-xs md:grid-cols-3 xl:grid-cols-6">
        <div className="rounded border border-terminal-line bg-black/25 px-2 py-2">Phase: {runtimePhaseLabel}</div>
        <div className="rounded border border-terminal-line bg-black/25 px-2 py-2">Brokers: {brokerConnectedCount}</div>
        <div className="rounded border border-terminal-line bg-black/25 px-2 py-2">Ready: {executionReadyCount}</div>
        <div className="rounded border border-terminal-line bg-black/25 px-2 py-2">Automation: {automationOn ? "ON" : "OFF"}</div>
        <div className="rounded border border-terminal-line bg-black/25 px-2 py-2">Scan Age: {scanAgeSeconds != null ? `${scanAgeSeconds.toFixed(0)}s` : "-"}</div>
        <div className="rounded border border-terminal-line bg-black/25 px-2 py-2">Context: {selectedBrokerLabel ?? "All Brokers"}</div>
      </div>
    </section>
  );
}
