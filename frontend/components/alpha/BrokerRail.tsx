type BrokerConnectionEntry = {
  provider: string;
  label: string;
  connected: boolean;
  configured?: boolean;
  planned?: boolean;
  connectable: boolean;
  status_label: string;
  capabilities: Record<string, boolean>;
};

type Props = {
  brokers: BrokerConnectionEntry[];
  selectedBrokerProvider: string | null;
  onSelectBroker: (provider: string | null) => void;
  onOpenDetails: (provider: string) => void;
};

function statusTone(broker: BrokerConnectionEntry): string {
  if (broker.connected) return "border-green-500/50 bg-green-500/12 text-green-100";
  if (broker.configured) return "border-cyan-500/50 bg-cyan-500/12 text-cyan-100";
  if (broker.planned) return "border-slate-500/50 bg-slate-500/10 text-slate-300";
  if (broker.connectable) return "border-amber-500/50 bg-amber-500/12 text-amber-100";
  return "border-red-500/50 bg-red-500/12 text-red-100";
}

function statusDot(broker: BrokerConnectionEntry): string {
  if (broker.connected) return "bg-green-400";
  if (broker.configured) return "bg-cyan-400";
  if (broker.planned) return "bg-slate-400";
  if (broker.connectable) return "bg-amber-400";
  return "bg-red-400";
}

export default function BrokerRail({
  brokers,
  selectedBrokerProvider,
  onSelectBroker,
  onOpenDetails,
}: Props) {
  return (
    <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-3">
      <div className="mb-2 flex items-center justify-between">
        <h2 className="text-xs font-semibold uppercase tracking-wider text-terminal-accent">Broker Context Rail</h2>
        <button
          type="button"
          onClick={() => onSelectBroker(null)}
          className="rounded border border-terminal-line px-2 py-1 text-[10px] text-slate-300 hover:border-terminal-accent/60"
        >
          All Brokers
        </button>
      </div>

      <div className="hidden space-y-2 lg:block">
        {brokers.map((broker) => {
          const selected = selectedBrokerProvider === broker.provider;
          return (
            <button
              key={broker.provider}
              type="button"
              onClick={() => onSelectBroker(selected ? null : broker.provider)}
              onDoubleClick={() => onOpenDetails(broker.provider)}
              className={`w-full rounded-lg border px-3 py-2 text-left text-xs transition ${statusTone(broker)} ${selected ? "ring-2 ring-terminal-accent/70" : ""}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold">{broker.label}</span>
                <span className={`h-2.5 w-2.5 rounded-full ${statusDot(broker)}`} />
              </div>
              <div className="mt-1 text-[10px] uppercase tracking-wider text-current/85">{broker.status_label}</div>
              <div className="mt-1 flex flex-wrap gap-1">
                {broker.capabilities.supports_equities && <span className="rounded border border-current/30 px-1.5 py-0.5 text-[9px]">Equities</span>}
                {broker.capabilities.supports_options && <span className="rounded border border-current/30 px-1.5 py-0.5 text-[9px]">Options</span>}
                {broker.capabilities.supports_crypto && <span className="rounded border border-current/30 px-1.5 py-0.5 text-[9px]">Crypto</span>}
              </div>
            </button>
          );
        })}
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1 lg:hidden">
        {brokers.map((broker) => {
          const selected = selectedBrokerProvider === broker.provider;
          return (
            <button
              key={broker.provider}
              type="button"
              onClick={() => onSelectBroker(selected ? null : broker.provider)}
              className={`min-w-[180px] rounded-lg border px-3 py-2 text-left text-xs ${statusTone(broker)} ${selected ? "ring-2 ring-terminal-accent/70" : ""}`}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-semibold">{broker.label}</span>
                <span className={`h-2.5 w-2.5 rounded-full ${statusDot(broker)}`} />
              </div>
              <div className="mt-1 text-[10px] uppercase tracking-wider text-current/85">{broker.status_label}</div>
            </button>
          );
        })}
      </div>

      <p className="mt-2 text-[10px] text-slate-500">Tip: click to set broker context. Double-click desktop tiles for full connection details.</p>
    </section>
  );
}
