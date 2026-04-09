import Link from "next/link";

export default function HomePage() {
  return (
    <main className="min-h-screen px-6 py-10 md:px-12 lg:px-20">
      <section className="mx-auto flex max-w-5xl flex-col gap-8 rounded-2xl border border-terminal-line bg-terminal-panel/70 p-8 shadow-glow">
        <span className="inline-block w-fit rounded-full border border-terminal-accent/60 px-3 py-1 text-xs uppercase tracking-wider text-terminal-accent">
          Production MVP
        </span>
        <h1 className="text-3xl font-semibold md:text-5xl">GHOST ALPHA TERMINAL</h1>
        <p className="max-w-2xl text-sm text-slate-300 md:text-base">
          AI-powered trading intelligence with Kronos-style forecasting, options analytics, and strategy signals.
          Built for fast iteration with a Python FastAPI backend and a Next.js terminal interface.
        </p>
        <div>
          <Link
            href="/dashboard"
            className="inline-flex items-center rounded-md bg-terminal-accent px-5 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-110"
          >
            Launch Dashboard
          </Link>
        </div>
      </section>
    </main>
  );
}
