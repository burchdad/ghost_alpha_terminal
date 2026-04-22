import Link from "next/link";
import NotificationBell from "./NotificationBell";

type ExecutionMode = "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING" | null;

type RuntimePhase = {
  label: string;
  tone: string;
};

type Props = {
  executionMode: ExecutionMode;
  runtimePhase: RuntimePhase;
  focusSymbol: string;
  selectedBrokerLabel: string | null;
  terminalHref: string;
};

function formatMode(mode: ExecutionMode): string {
  if (!mode) return "UNKNOWN";
  return mode.replaceAll("_", " ");
}

export default function AlphaHeader({
  executionMode,
  runtimePhase,
  focusSymbol,
  selectedBrokerLabel,
  terminalHref,
}: Props) {
  return (
    <header className="mb-4 rounded-xl border border-terminal-line bg-terminal-panel/70 px-4 py-3">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold md:text-2xl">Market Intelligence Dashboard</h1>
          <p className="text-xs text-slate-400">Mission-control discovery, risk, and execution context in one operator cockpit.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded border border-cyan-500/40 bg-cyan-500/10 px-2 py-1 text-[11px] text-cyan-200">
            Mode: {formatMode(executionMode)}
          </span>
          <span className={`rounded border px-2 py-1 text-[11px] ${runtimePhase.tone}`}>
            Phase: {runtimePhase.label}
          </span>
          {selectedBrokerLabel ? (
            <span className="rounded border border-amber-500/40 bg-amber-500/10 px-2 py-1 text-[11px] text-amber-200">
              Broker: {selectedBrokerLabel}
            </span>
          ) : (
            <span className="rounded border border-slate-500/40 bg-slate-500/10 px-2 py-1 text-[11px] text-slate-300">
              Broker: All Brokers
            </span>
          )}
          <Link
            href={`/news?symbol=${encodeURIComponent(focusSymbol)}`}
            className="rounded border border-terminal-line px-3 py-1.5 text-xs text-slate-300 hover:border-terminal-accent/50"
          >
            Open News Dashboard
          </Link>
          <Link
            href={terminalHref}
            className="rounded border border-terminal-line px-3 py-1.5 text-xs text-slate-300 hover:border-terminal-accent/50"
          >
            Open Deep Terminal ({focusSymbol})
          </Link>
          <NotificationBell />
        </div>
      </div>
    </header>
  );
}
