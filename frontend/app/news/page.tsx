"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";

import NewsPanel from "../../components/NewsPanel";
import { apiFetch } from "../../lib/apiClient";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type NewsSignal = {
  symbol: string;
  timestamp: string;
  data_classification: "PUBLIC" | "DERIVED" | "RESTRICTED" | "UNKNOWN";
  sources_used: string[];
  sentiment_score: number;
  news_momentum_score: number;
  event_strength: number;
  event_flags: string[];
  rationale: string;
};

type NewsAuditEntry = {
  timestamp: string;
  symbol: string;
  data_classification: "PUBLIC" | "DERIVED" | "RESTRICTED" | "UNKNOWN";
  sources_used: string[];
  sentiment_score: number;
  news_momentum_score: number;
  event_strength: number;
  event_flags: string[];
};

type NewsHeadline = {
  source: string;
  title: string;
  url: string;
  published_at: string | null;
  summary: string;
  relevance: number;
};

type NewsSourceStatus = {
  source: string;
  url: string;
  status: string;
  headline_count: number;
  weight: number;
  last_success_at: string | null;
  last_error: string | null;
};

type NewsDashboardResponse = {
  signal: NewsSignal;
  headlines: NewsHeadline[];
  audit: NewsAuditEntry[];
  sources: string[];
  source_status: NewsSourceStatus[];
  stream_status: {
    running?: boolean;
    connected?: boolean;
    products?: string[];
    [key: string]: unknown;
  };
};

function NewsDashboardContent() {
  const searchParams = useSearchParams();
  const initialSymbol = (searchParams.get("symbol") || "SPY").toUpperCase();
  const [symbolInput, setSymbolInput] = useState(initialSymbol);
  const [activeSymbol, setActiveSymbol] = useState(initialSymbol);
  const [dashboard, setDashboard] = useState<NewsDashboardResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setSymbolInput(initialSymbol);
    setActiveSymbol(initialSymbol);
  }, [initialSymbol]);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setLoading(true);
      setError(null);
      try {
        const response = await apiFetch(`${API_BASE}/agents/news/dashboard?symbol=${encodeURIComponent(activeSymbol)}&limit=30`);
        if (!response.ok) {
          throw new Error(`News dashboard request failed with ${response.status}`);
        }
        const payload = (await response.json()) as NewsDashboardResponse;
        if (!cancelled) {
          setDashboard(payload);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load news dashboard.");
          setDashboard(null);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void loadDashboard();
    const interval = window.setInterval(() => {
      void loadDashboard();
    }, 45000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [activeSymbol]);

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(34,197,94,0.12),_transparent_35%),linear-gradient(180deg,_rgba(2,6,23,0.98),_rgba(2,6,23,1))] px-4 py-6 text-slate-100 md:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="rounded-2xl border border-terminal-line bg-terminal-panel/70 px-5 py-4 backdrop-blur">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="text-[11px] uppercase tracking-[0.24em] text-terminal-accent">Ghost Alpha News Grid</div>
              <h1 className="mt-2 text-2xl font-semibold">Standalone News Dashboard</h1>
              <p className="mt-1 max-w-3xl text-sm text-slate-400">
                Aggregated public market feeds, live macro headlines, and symbol-level news scoring in a dedicated workspace.
              </p>
            </div>
            <div className="flex flex-wrap gap-2 text-xs">
              <Link href="/alpha" className="rounded border border-terminal-line px-3 py-2 text-slate-300 hover:border-terminal-accent/50">
                Back To Alpha
              </Link>
              <Link
                href={`/terminal?symbol=${encodeURIComponent(activeSymbol)}`}
                className="rounded border border-terminal-line px-3 py-2 text-slate-300 hover:border-terminal-accent/50"
              >
                Open Deep Terminal
              </Link>
            </div>
          </div>

          <form
            className="mt-4 flex flex-wrap items-center gap-3"
            onSubmit={(event) => {
              event.preventDefault();
              const normalized = symbolInput.trim().toUpperCase();
              if (normalized) {
                setActiveSymbol(normalized);
              }
            }}
          >
            <input
              value={symbolInput}
              onChange={(event) => setSymbolInput(event.target.value.toUpperCase())}
              className="min-w-[180px] rounded border border-terminal-line bg-black/20 px-3 py-2 text-sm text-slate-100 outline-none placeholder:text-slate-500"
              placeholder="Enter symbol or ETF"
            />
            <button type="submit" className="rounded bg-terminal-accent px-3 py-2 text-sm font-medium text-slate-950">
              Refresh Symbol
            </button>
            <div className="text-xs text-slate-400">
              Tracking {activeSymbol} · auto-refresh every 45s · sources {dashboard?.sources.length ?? 0}
            </div>
          </form>
        </header>

        {error ? (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">{error}</div>
        ) : null}

        <section className="grid gap-4 lg:grid-cols-[340px,minmax(0,1fr)]">
          <aside className="space-y-4">
            <NewsPanel signal={dashboard?.signal ?? null} audit={dashboard?.audit ?? null} />

            <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-terminal-accent">Live Ingest Status</h2>
                <span className="text-[11px] text-slate-400">{loading ? "Refreshing" : "Live"}</span>
              </div>
              <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-300">
                <div className="rounded border border-terminal-line bg-black/20 p-2">
                  Coinbase WS: {dashboard?.stream_status.connected ? "Connected" : "Offline"}
                </div>
                <div className="rounded border border-terminal-line bg-black/20 p-2">
                  Feed Sources: {dashboard?.source_status.filter((item) => item.status === "ok").length ?? 0}
                </div>
              </div>
            </div>
          </aside>

          <div className="space-y-4">
            <section className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-terminal-accent">Headline Feed</h2>
                <div className="text-xs text-slate-400">Sorted by relevance to {activeSymbol} and recency</div>
              </div>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {(dashboard?.headlines ?? []).map((headline) => (
                  <a
                    key={`${headline.source}-${headline.url}`}
                    href={headline.url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-xl border border-terminal-line bg-black/20 p-4 transition hover:border-terminal-accent/50"
                  >
                    <div className="flex items-center justify-between gap-2 text-[10px] uppercase tracking-[0.2em] text-slate-500">
                      <span>{headline.source.replaceAll("_", " ")}</span>
                      <span>R {headline.relevance.toFixed(2)}</span>
                    </div>
                    <h3 className="mt-2 text-sm font-semibold text-slate-100">{headline.title}</h3>
                    <p className="mt-2 text-xs leading-5 text-slate-400">{headline.summary || "No summary available."}</p>
                    <div className="mt-3 text-[11px] text-slate-500">
                      {headline.published_at ? new Date(headline.published_at).toLocaleString() : "Timestamp unavailable"}
                    </div>
                  </a>
                ))}
                {!loading && (dashboard?.headlines.length ?? 0) === 0 ? (
                  <div className="rounded-xl border border-terminal-line bg-black/20 p-4 text-sm text-slate-400">
                    No matching headlines found for {activeSymbol}. Try a broader symbol like SPY, QQQ, BTCUSD, or AAPL.
                  </div>
                ) : null}
              </div>
            </section>

            <section className="grid gap-4 xl:grid-cols-[1.1fr,0.9fr]">
              <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-terminal-accent">Source Coverage</h2>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {(dashboard?.source_status ?? []).map((source) => (
                    <div key={source.source} className="rounded border border-terminal-line bg-black/20 p-3 text-xs text-slate-300">
                      <div className="flex items-center justify-between gap-2">
                        <span className="font-semibold text-slate-100">{source.source.replaceAll("_", " ")}</span>
                        <span className={source.status === "ok" ? "text-emerald-300" : "text-red-300"}>{source.status}</span>
                      </div>
                      <div className="mt-1">Headlines: {source.headline_count}</div>
                      <div className="mt-1">Weight: {source.weight.toFixed(1)}</div>
                      <div className="mt-1 truncate text-slate-500">{source.url}</div>
                      <div className="mt-1 text-slate-500">
                        {source.last_success_at ? `Last success ${new Date(source.last_success_at).toLocaleTimeString()}` : source.last_error || "No successful pull yet."}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
                <h2 className="text-sm font-semibold uppercase tracking-wider text-terminal-accent">Recent Audit</h2>
                <div className="mt-4 space-y-2 text-xs text-slate-300">
                  {(dashboard?.audit ?? []).slice(0, 10).map((entry) => (
                    <div key={`${entry.symbol}-${entry.timestamp}`} className="rounded border border-terminal-line bg-black/20 p-3">
                      <div className="flex items-center justify-between gap-2 text-[11px] text-slate-500">
                        <span>{entry.symbol}</span>
                        <span>{new Date(entry.timestamp).toLocaleTimeString()}</span>
                      </div>
                      <div className="mt-2">
                        Sentiment {entry.sentiment_score.toFixed(2)} · Momentum {entry.news_momentum_score.toFixed(2)} · Event {entry.event_strength.toFixed(2)}
                      </div>
                      <div className="mt-2 text-slate-500">{entry.sources_used.join(", ")}</div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </div>
        </section>
      </div>
    </main>
  );
}

export default function NewsDashboardPage() {
  return (
    <Suspense
      fallback={
        <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(34,197,94,0.12),_transparent_35%),linear-gradient(180deg,_rgba(2,6,23,0.98),_rgba(2,6,23,1))] px-4 py-6 text-slate-100 md:px-8">
          <div className="mx-auto max-w-7xl rounded-2xl border border-terminal-line bg-terminal-panel/70 px-5 py-8 text-sm text-slate-300 backdrop-blur">
            Loading news dashboard...
          </div>
        </main>
      }
    >
      <NewsDashboardContent />
    </Suspense>
  );
}