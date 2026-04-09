"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import OrchestratorPanel, {
  type OrchestratorScan,
  type OrchestratorStatus,
} from "../../components/OrchestratorPanel";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

async function parseJsonOrNull<T>(res: Response): Promise<T | null> {
  if (!res.ok) {
    return null;
  }
  try {
    return (await res.json()) as T;
  } catch {
    return null;
  }
}

export default function AlphaPage() {
  const router = useRouter();
  const [scan, setScan] = useState<OrchestratorScan | null>(null);
  const [status, setStatus] = useState<OrchestratorStatus | null>(null);
  const [loading, setLoading] = useState(false);

  const strategyCounts = useMemo(() => {
    const counts: Record<string, number> = {
      OPTIONS_PLAY: 0,
      SWING_TRADE: 0,
      DAY_TRADE: 0,
      SCALP: 0,
      WATCH: 0,
      IGNORE: 0,
    };
    for (const c of scan?.candidates ?? []) {
      counts[c.strategy_type] = (counts[c.strategy_type] ?? 0) + 1;
    }
    return counts;
  }, [scan]);

  useEffect(() => {
    async function boot() {
      const [statusRes, latestRes] = await Promise.all([
        fetch(`${API_BASE}/orchestrator/status`),
        fetch(`${API_BASE}/orchestrator/scan/latest`),
      ]);
      const statusData = await parseJsonOrNull<OrchestratorStatus>(statusRes);
      const latestData = await parseJsonOrNull<OrchestratorScan>(latestRes);
      setStatus(statusData);
      if (latestData) {
        setScan(latestData);
        return;
      }
      setLoading(true);
      try {
        const scanRes = await fetch(`${API_BASE}/orchestrator/scan?limit=25`, { method: "POST" });
        const scanData = await parseJsonOrNull<OrchestratorScan>(scanRes);
        setScan(scanData);
        const refreshed = await fetch(`${API_BASE}/orchestrator/status`);
        const refreshedStatus = await parseJsonOrNull<OrchestratorStatus>(refreshed);
        setStatus(refreshedStatus);
      } finally {
        setLoading(false);
      }
    }

    boot().catch((err: unknown) => {
      console.error("Failed to load alpha dashboard", err);
    });
  }, []);

  async function handleScan() {
    setLoading(true);
    try {
      const scanRes = await fetch(`${API_BASE}/orchestrator/scan?limit=25`, { method: "POST" });
      const scanData = await parseJsonOrNull<OrchestratorScan>(scanRes);
      setScan(scanData);
      const statusRes = await fetch(`${API_BASE}/orchestrator/status`);
      const statusData = await parseJsonOrNull<OrchestratorStatus>(statusRes);
      setStatus(statusData);
    } finally {
      setLoading(false);
    }
  }

  async function handleToggleAuto(enabled: boolean) {
    await fetch(`${API_BASE}/orchestrator/mode`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ auto_mode: enabled }),
    });
    const statusRes = await fetch(`${API_BASE}/orchestrator/status`);
    const statusData = await parseJsonOrNull<OrchestratorStatus>(statusRes);
    setStatus(statusData);
  }

  function drillIntoSymbol(symbol: string) {
    router.push(`/terminal?symbol=${encodeURIComponent(symbol)}`);
  }

  return (
    <main className="min-h-screen p-4 md:p-6">
      <div className="mb-4 flex items-center justify-between rounded-xl border border-terminal-line bg-terminal-panel/70 px-4 py-3">
        <div>
          <h1 className="text-lg font-semibold md:text-2xl">MARKET INTELLIGENCE DASHBOARD</h1>
          <p className="text-xs text-slate-400">Layer 1: Discovery and ranking across the full market universe</p>
        </div>
        <Link
          href="/terminal"
          className="rounded border border-terminal-line px-3 py-1.5 text-xs text-slate-300 hover:border-terminal-accent/50"
        >
          Open Deep Terminal
        </Link>
      </div>

      <section className="mb-4 grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Coverage</div>
          <div className="mt-2 text-2xl font-semibold text-terminal-accent">{scan?.total_scanned ?? 0}</div>
          <div className="text-xs text-slate-400">Tickers scanned per cycle</div>
        </div>
        <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Execution Ready</div>
          <div className="mt-2 text-2xl font-semibold text-green-400">
            {(scan?.candidates ?? []).filter((c) => c.action_label === "EXECUTE").length}
          </div>
          <div className="text-xs text-slate-400">Candidates cleared for run</div>
        </div>
        <div className="rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
          <div className="text-[11px] uppercase tracking-wider text-slate-500">Auto Mode</div>
          <div className={`mt-2 text-2xl font-semibold ${status?.auto_mode ? "text-green-400" : "text-slate-300"}`}>
            {status?.auto_mode ? "ON" : "OFF"}
          </div>
          <div className="text-xs text-slate-400">Interval: {status?.auto_interval_seconds ?? 300}s</div>
        </div>
      </section>

      <section className="mb-4 rounded-xl border border-terminal-line bg-terminal-panel/60 p-4">
        <h2 className="mb-2 text-sm font-semibold text-terminal-accent">Strategy Distribution</h2>
        <div className="grid grid-cols-2 gap-2 text-xs md:grid-cols-6">
          <div className="rounded border border-terminal-line px-2 py-2">OPTIONS: {strategyCounts.OPTIONS_PLAY}</div>
          <div className="rounded border border-terminal-line px-2 py-2">SWING: {strategyCounts.SWING_TRADE}</div>
          <div className="rounded border border-terminal-line px-2 py-2">DAY: {strategyCounts.DAY_TRADE}</div>
          <div className="rounded border border-terminal-line px-2 py-2">SCALP: {strategyCounts.SCALP}</div>
          <div className="rounded border border-terminal-line px-2 py-2">WATCH: {strategyCounts.WATCH}</div>
          <div className="rounded border border-terminal-line px-2 py-2">IGNORE: {strategyCounts.IGNORE}</div>
        </div>
      </section>

      <OrchestratorPanel
        scan={scan}
        status={status}
        loading={loading}
        onScan={handleScan}
        onToggleAutoMode={handleToggleAuto}
        onRunSymbol={drillIntoSymbol}
      />
    </main>
  );
}
