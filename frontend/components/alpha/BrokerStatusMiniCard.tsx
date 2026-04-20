type BrokerConnectionEntry = {
  provider: string;
  label: string;
  connected: boolean;
  configured?: boolean;
  status_label: string;
  mode: string | null;
  permissions: string;
  last_error: string | null;
};

type Props = {
  broker: BrokerConnectionEntry | null;
};

export default function BrokerStatusMiniCard({ broker }: Props) {
  if (!broker) {
    return (
      <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3 text-xs text-slate-400">
        No broker context selected. Operating in all-brokers mode.
      </div>
    );
  }

  const tone = broker.connected
    ? "border-green-500/40 bg-green-500/10 text-green-100"
    : broker.configured
      ? "border-cyan-500/40 bg-cyan-500/10 text-cyan-100"
      : "border-amber-500/40 bg-amber-500/10 text-amber-100";

  return (
    <div className={`rounded-xl border p-3 text-xs ${tone}`}>
      <div className="font-semibold">{broker.label}</div>
      <div className="mt-1">{broker.status_label}</div>
      <div className="mt-1 text-current/90">Mode: {broker.mode ?? "N/A"}</div>
      <div className="text-current/90">Permissions: {broker.permissions}</div>
      {broker.last_error ? <div className="mt-1 text-red-300">Error: {broker.last_error}</div> : null}
    </div>
  );
}
