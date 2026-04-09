import Link from "next/link";

export default function HomePage() {
  return (
    <main className="relative min-h-screen overflow-hidden px-5 py-8 md:px-10 md:py-10 lg:px-16">
      <div
        aria-hidden
        className="pointer-events-none absolute -left-24 top-12 h-72 w-72 rounded-full bg-cyan-400/10 blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -right-24 top-40 h-80 w-80 rounded-full bg-amber-400/10 blur-3xl"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute bottom-0 left-1/2 h-80 w-[42rem] -translate-x-1/2 rounded-full bg-cyan-500/10 blur-3xl"
      />

      <section className="relative mx-auto flex max-w-6xl flex-col gap-6 rounded-3xl border border-terminal-line bg-[#05121ab8] p-6 shadow-glow md:p-8">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-terminal-line/40 pb-4">
          <div className="flex flex-wrap items-center gap-2 text-[11px] uppercase tracking-widest">
            <span className="rounded-full border border-terminal-accent/70 bg-terminal-accent/10 px-3 py-1 text-terminal-accent">
              GhostAlpha OS
            </span>
            <span className="rounded-full border border-emerald-400/40 bg-emerald-400/10 px-3 py-1 text-emerald-300">
              Market Brain Online
            </span>
          </div>
          <nav className="flex items-center gap-4 text-xs text-slate-300">
            <Link href="/alpha" className="transition hover:text-terminal-accent">
              Market Dashboard
            </Link>
            <Link href="/terminal" className="transition hover:text-terminal-accent">
              Deep Terminal
            </Link>
            <Link href="/privacy-policy" className="transition hover:text-terminal-accent">
              Privacy
            </Link>
            <Link href="/terms-of-use" className="transition hover:text-terminal-accent">
              Terms
            </Link>
          </nav>
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-5">
            <h1 className="text-3xl font-semibold leading-tight md:text-5xl">
              GHOST ALPHA TERMINAL
              <span className="mt-2 block text-lg font-medium text-terminal-accent md:text-2xl">
                Market Discovery -&gt; Execution Command
              </span>
            </h1>
            <p className="max-w-3xl text-sm text-slate-300 md:text-base">
              Scan the full market universe, rank opportunities by strategy fit, then drill into a deep AI terminal for
              execution, risk, replay, and controls.
            </p>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-xl border border-terminal-line/70 bg-black/25 p-3">
                <div className="text-[11px] uppercase tracking-wider text-slate-500">Coverage</div>
                <div className="mt-1 text-2xl font-semibold text-terminal-accent">321</div>
                <div className="text-xs text-slate-400">Tradables in universe</div>
              </div>
              <div className="rounded-xl border border-terminal-line/70 bg-black/25 p-3">
                <div className="text-[11px] uppercase tracking-wider text-slate-500">Architecture</div>
                <div className="mt-1 text-lg font-semibold text-cyan-300">Two Tier</div>
                <div className="text-xs text-slate-400">Discovery + execution</div>
              </div>
              <div className="rounded-xl border border-terminal-line/70 bg-black/25 p-3">
                <div className="text-[11px] uppercase tracking-wider text-slate-500">Mode</div>
                <div className="mt-1 text-lg font-semibold text-emerald-300">Operator Ready</div>
                <div className="text-xs text-slate-400">Manual or auto flow</div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <Link
                href="/alpha"
                className="inline-flex items-center rounded-lg border border-cyan-300/60 bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110"
              >
                Open Market Intelligence
              </Link>
              <Link
                href="/terminal"
                className="inline-flex items-center rounded-lg border border-terminal-line px-5 py-3 text-sm font-semibold text-slate-200 transition hover:border-terminal-accent/70 hover:text-terminal-accent"
              >
                Open Deep Terminal
              </Link>
            </div>
          </div>

          <div className="rounded-2xl border border-terminal-line/70 bg-[#031018d1] p-4 md:p-5">
            <div className="mb-3 text-xs uppercase tracking-wider text-slate-500">Workflow</div>
            <ol className="space-y-3 text-sm text-slate-300">
              <li className="rounded-lg border border-terminal-line/60 bg-black/20 p-3">
                <div className="text-xs text-cyan-300">01 - Market Dashboard</div>
                <div className="mt-1">Scan, rank, and filter opportunities across the full universe.</div>
              </li>
              <li className="rounded-lg border border-terminal-line/60 bg-black/20 p-3">
                <div className="text-xs text-cyan-300">02 - Strategy Routing</div>
                <div className="mt-1">Assign options, swing, day-trade, scalp, watch, or ignore.</div>
              </li>
              <li className="rounded-lg border border-terminal-line/60 bg-black/20 p-3">
                <div className="text-xs text-cyan-300">03 - Deep Terminal</div>
                <div className="mt-1">Run full pipeline: context, risk, execution, and replay lineage.</div>
              </li>
            </ol>
            <div className="mt-4 rounded-lg border border-amber-300/40 bg-amber-300/10 p-3 text-xs text-amber-100">
              Tip: start with Market Intelligence, then click into the highest-ranked candidate for execution.
            </div>
          </div>
        </div>

        <div className="grid gap-3 border-t border-terminal-line/40 pt-4 text-xs text-slate-400 sm:grid-cols-3">
          <div className="rounded-lg border border-terminal-line/60 bg-black/20 p-3">
            Orchestrator Layer: discovery, ranking, strategy selection.
          </div>
          <div className="rounded-lg border border-terminal-line/60 bg-black/20 p-3">
            Execution Layer: controls, risk rails, decision replay.
          </div>
          <div className="rounded-lg border border-terminal-line/60 bg-black/20 p-3">
            URL Model: /alpha -&gt; /terminal?symbol=TSLA.
          </div>
        </div>

        <div className="grid gap-3 border-t border-terminal-line/40 pt-4 md:grid-cols-3">
          <div className="rounded-xl border border-terminal-line/60 bg-black/20 p-4">
            <h3 className="text-sm font-semibold text-terminal-accent">Why Traders Use It</h3>
            <p className="mt-2 text-xs leading-relaxed text-slate-300">
              Instead of manually jumping between tickers, the orchestrator continuously surfaces the highest-quality
              opportunities and routes them by strategy fit.
            </p>
          </div>
          <div className="rounded-xl border border-terminal-line/60 bg-black/20 p-4">
            <h3 className="text-sm font-semibold text-terminal-accent">What You Keep</h3>
            <p className="mt-2 text-xs leading-relaxed text-slate-300">
              Your existing execution stack is unchanged: context intelligence, risk guardrails, control panel,
              execution history, and decision replay are all preserved.
            </p>
          </div>
          <div className="rounded-xl border border-terminal-line/60 bg-black/20 p-4">
            <h3 className="text-sm font-semibold text-terminal-accent">Go Live Fast</h3>
            <p className="mt-2 text-xs leading-relaxed text-slate-300">
              Start in Market Intelligence, pick a ranked setup, and jump into deep ticker analysis with one click.
              Built for operator speed and iterative model tuning.
            </p>
          </div>
        </div>

        <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-terminal-line/40 pt-4 text-xs text-slate-400">
          <p>Ghost Alpha Terminal - AI-driven market operating system</p>
          <div className="flex items-center gap-4">
            <Link href="/privacy-policy" className="transition hover:text-terminal-accent">
              Privacy Policy
            </Link>
            <Link href="/terms-of-use" className="transition hover:text-terminal-accent">
              Terms of Use
            </Link>
          </div>
        </footer>
      </section>
    </main>
  );
}
