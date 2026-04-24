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
    <header className="mb-6 border-b border-terminal-line pb-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="mb-0.5 text-[10px] font-bold uppercase tracking-widest text-terminal-accent">Ghost Alpha</div>
          <h1 className="text-xl font-semibold text-slate-100 md:text-2xl">Alpha Operations</h1>
          <p className="mt-1 text-xs text-slate-500">Your daily execution engine. Discovery, risk, and operator control.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            href={`/news?symbol=${encodeURIComponent(focusSymbol)}`}
            className="rounded-lg border border-terminal-line px-3 py-1.5 text-xs text-slate-300 transition hover:border-terminal-accent/50 hover:text-terminal-accent"
          >
            News
          </Link>
          <Link
            href={terminalHref}
            className="rounded-lg border border-terminal-accent/40 bg-terminal-accent/10 px-3 py-1.5 text-xs text-terminal-accent transition hover:bg-terminal-accent/20"
          >
            Terminal · {focusSymbol}
          </Link>
          <NotificationBell />
        </div>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <span className="rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2.5 py-0.5 text-[11px] text-cyan-300">
          {formatMode(executionMode)}
        </span>
        <span className={`rounded-full border px-2.5 py-0.5 text-[11px] ${runtimePhase.tone} border-current/20 bg-current/5`}>
          {runtimePhase.label}
        </span>
        <span className="rounded-full border border-slate-600/40 bg-slate-600/10 px-2.5 py-0.5 text-[11px] text-slate-300">
          Focus: {focusSymbol}
        </span>
        {selectedBrokerLabel && (
          <span className="rounded-full border border-amber-500/40 bg-amber-500/10 px-2.5 py-0.5 text-[11px] text-amber-300">
            {selectedBrokerLabel}
          </span>
        )}
      </div>
    </header>
  );
}
