"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { ensureHighTrust } from "../../lib/highTrust";
import { apiFetch } from "../../lib/apiClient";
import DashboardCopilot from "../../components/DashboardCopilot";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";
const POST_CONNECT_PROMPT_KEY = "alpaca-post-connect-prompt";

const BROKER_ORDER = ["alpaca", "coinbase", "tradier", "schwab", "tastytrade", "robinhood", "tradestation"];

type BrokerStatusEntry = {
  connected: boolean;
  configured?: boolean;
  planned?: boolean;
  label?: string;
  accounts?: string[];
};

type BrokerStatusResponse = Record<string, BrokerStatusEntry>;

type AuthMeResponse = {
  user: {
    id: string;
    email: string;
  };
};

export default function BrokeragesPage() {
  const router = useRouter();
  const [userEmail, setUserEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [brokers, setBrokers] = useState<BrokerStatusResponse>({});
  const [connecting, setConnecting] = useState<string | null>(null);
  const [showPostConnectPrompt, setShowPostConnectPrompt] = useState(false);


  async function fetchSessionAndStatus() {
    setLoading(true);
    setError("");
    try {
      const [meRes, brokerRes] = await Promise.all([
        apiFetch(`${API_BASE}/auth/me`, { apiBase: API_BASE }),
        apiFetch(`${API_BASE}/brokers/status`, { apiBase: API_BASE }),
      ]);

      if (meRes.status === 401 || brokerRes.status === 401) {
        router.replace("/login?next=/brokerages");
        return;
      }

      if (!meRes.ok) {
        throw new Error("Failed to load session");
      }
      if (!brokerRes.ok) {
        throw new Error("Failed to load broker status");
      }

      const me = (await meRes.json()) as AuthMeResponse;
      const status = (await brokerRes.json()) as BrokerStatusResponse;
      setUserEmail(me.user.email);
      setBrokers(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load broker setup");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // Refresh broker status on mount, especially after OAuth callback
    const oauthState = typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("alpaca_oauth");
    if (oauthState === "connected") {
      console.log("[BrokeragesMount] OAuth callback detected, fetching fresh broker status...");
    }
    void fetchSessionAndStatus();
  }, []);

  const cards = useMemo(() => {
    const keys = BROKER_ORDER.filter((k) => k in brokers).concat(
      Object.keys(brokers).filter((k) => !BROKER_ORDER.includes(k)),
    );
    return keys.map((key) => {
      const entry = brokers[key] ?? { connected: false, accounts: [] };
      return {
        key,
        label: entry.label || key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
        status: entry,
      };
    });
  }, [brokers]);

  const hasConnectedBroker = useMemo(() => {
    return cards.some((card) => Boolean(card.status.connected) || Boolean(card.status.configured));
  }, [cards]);


  // Show modal if OAuth callback succeeded and Alpaca is connected.
  useEffect(() => {
    if (loading) return;

    const oauthParam = typeof window === "undefined" ? null : new URLSearchParams(window.location.search).get("alpaca_oauth");
    const alpacaConnected = Boolean(brokers.alpaca?.connected);

    console.log("[BrokeragesOAuth]", { oauthParam, alpacaConnected, loading });

    if (oauthParam === "connected" && alpacaConnected) {
      console.log("[BrokeragesModal] Showing post-connect prompt");
      setShowPostConnectPrompt(true);
    }
  }, [loading, brokers.alpaca?.connected]);

  function handleStayOnBrokerages() {
    setShowPostConnectPrompt(false);
    try {
      window.sessionStorage.removeItem(POST_CONNECT_PROMPT_KEY);
    } catch {
      // Ignore storage access failures and continue navigation.
    }
    router.replace("/brokerages");
  }

  function handleContinueToDashboard() {
    setShowPostConnectPrompt(false);
    try {
      window.sessionStorage.removeItem(POST_CONNECT_PROMPT_KEY);
    } catch {
      // Ignore storage access failures and continue navigation.
    }
    router.push("/dashboard");
  }

  async function handleConnect(provider: string) {
    if (provider !== "alpaca") {
      return;
    }
    setConnecting(provider);
    setError("");
    try {
      const ok = await ensureHighTrust({ apiBase: API_BASE });
      if (!ok) {
        setError("Security verification was cancelled.");
        return;
      }
      try {
        window.sessionStorage.setItem(POST_CONNECT_PROMPT_KEY, "1");
      } catch {
        // Ignore storage access failures and fall back to URL-based detection.
      }
      window.location.href = `${API_BASE}/alpaca/oauth/start?next=/brokerages`;
    } catch (err) {
      if (err instanceof Error && err.message === "Authentication required") {
        router.replace("/login?next=/brokerages");
        return;
      }
      setError(err instanceof Error ? err.message : "Unable to start secure connect flow");
    } finally {
      setConnecting(null);
    }
  }

  return (
    <main className="min-h-screen bg-slate-950 px-6 py-10 text-slate-100">
      <div className="mx-auto max-w-5xl">
        <header className="mb-8">
          <h1 className="text-3xl font-semibold tracking-tight">Connect Your Brokerage</h1>
          <p className="mt-2 text-sm text-slate-400">
            Connect at least one brokerage account to activate your trading workspace.
          </p>
          {userEmail ? <p className="mt-1 text-xs text-slate-500">Signed in as {userEmail}</p> : null}
        </header>

        {loading ? <p className="text-sm text-slate-400">Loading broker options...</p> : null}
        {error ? (
          <p className="mb-4 rounded-md border border-red-800 bg-red-950/40 px-3 py-2 text-sm text-red-200">{error}</p>
        ) : null}

        <section className="grid gap-4 sm:grid-cols-2 md:grid-cols-3">
          {cards.map((card) => {
            const connected = Boolean(card.status.connected);
            const configured = Boolean(card.status.configured);
            const planned = Boolean(card.status.planned);
            const busy = connecting === card.key;
            const canConnect = card.key === "alpaca";

            const statusText = connected
              ? "Connected"
              : configured
                ? "Platform Configured"
                : planned
                  ? "Integration Planned"
                  : "Not Connected";

            const borderColor = connected
              ? "border-emerald-700"
              : configured
                ? "border-cyan-800"
                : planned
                  ? "border-slate-700"
                  : "border-slate-800";

            return (
              <article key={card.key} className={`rounded-xl border bg-slate-900/60 p-4 ${borderColor}`}>
                <h2 className="text-lg font-medium">{card.label}</h2>
                <p
                  className={`mt-2 text-sm ${connected ? "text-emerald-300" : configured ? "text-cyan-300" : "text-slate-400"}`}
                >
                  {statusText}
                </p>
                {!planned && (
                  <div className="mt-4 flex gap-2">
                    <button
                      type="button"
                      disabled={!canConnect || busy}
                      onClick={() => handleConnect(card.key)}
                      className="rounded-md bg-emerald-600 px-3 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:opacity-40"
                    >
                      {busy ? "Redirecting..." : connected ? "Reconnect" : "Connect"}
                    </button>
                  </div>
                )}
              </article>
            );
          })}
        </section>

        <div className="mt-8 flex flex-wrap gap-3">
          <button
            type="button"
            disabled={!hasConnectedBroker}
            onClick={() => router.push("/dashboard")}
            className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
          >
            Continue to Dashboard
          </button>
          <button
            type="button"
            onClick={() => void fetchSessionAndStatus()}
            className="rounded-md border border-slate-700 px-4 py-2 text-sm hover:border-slate-500"
          >
            Refresh Status
          </button>
        </div>
      </div>

      {showPostConnectPrompt ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/70 px-4" role="dialog" aria-modal="true" aria-labelledby="post-connect-title">
          <div className="w-full max-w-lg rounded-xl border border-cyan-700/40 bg-slate-900 p-6 shadow-2xl">
            <h2 id="post-connect-title" className="text-xl font-semibold text-slate-100">
              Brokerage Connected
            </h2>
            <p className="mt-3 text-sm text-slate-300">
              Would you like to add any more accounts before proceeding to dashboard?
            </p>
            <div className="mt-6 flex flex-col gap-3 sm:flex-row">
              <button
                type="button"
                onClick={handleStayOnBrokerages}
                className="rounded-md border border-slate-600 px-4 py-2 text-sm font-medium text-slate-100 hover:border-slate-400"
              >
                Yes, connect more accounts
              </button>
              <button
                type="button"
                onClick={handleContinueToDashboard}
                className="rounded-md bg-emerald-600 px-4 py-2 text-sm font-semibold text-white hover:bg-emerald-500"
              >
                No, continue to dashboard
              </button>
            </div>
          </div>
        </div>
      ) : null}
      <DashboardCopilot />
    </main>
  );
}


