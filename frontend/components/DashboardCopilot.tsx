"use client";

import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "../lib/apiClient";
import { ensureHighTrust } from "../lib/highTrust";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type CopilotState = {
  execution_mode: "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING";
  copilot_mode_assigned?: string;
  scan_auto_mode: boolean;
  autonomous_enabled: boolean;
  autonomous_cycles_run: number;
  account_balance: number;
  daily_loss_limit_pct: number;
  max_drawdown_limit_pct: number;
  goal_enabled: boolean;
  goal_target_capital: number | null;
  goal_timeframe_days: number | null;
  live_only_during_market_hours: boolean;
  market_timezone: string;
  market_open_hhmm: string;
  market_close_hhmm: string;
};

type ContextMessage = {
  role: string;
  text: string;
  timestamp: string;
};

type ContextResponse = {
  greeting: string;
  first_name: string;
  state: CopilotState;
  history: ContextMessage[];
};

type ChatResponse = {
  reply: string;
  state: CopilotState;
  actions_applied: string[];
  requires_confirmation: boolean;
  confirmation_prompt: string | null;
  pending_action: { action: string; params: Record<string, unknown> } | null;
  copilot_mode?: string;
  parser_used?: string;
};

type Msg = {
  id: string;
  role: "assistant" | "user";
  text: string;
};

function shortMode(mode: CopilotState["execution_mode"]) {
  if (mode === "LIVE_TRADING") return "LIVE";
  if (mode === "PAPER_TRADING") return "PAPER";
  return "SIM";
}

export default function DashboardCopilot() {
  const [open, setOpen] = useState(true);
  const [loading, setLoading] = useState(false);
  const [sending, setSending] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [state, setState] = useState<CopilotState | null>(null);
  const [pendingAction, setPendingAction] = useState<{ action: string; params: Record<string, unknown> } | null>(null);

  useEffect(() => {
    async function boot() {
      setLoading(true);
      try {
        const res = await apiFetch(`${API_BASE}/copilot/context`, { apiBase: API_BASE });
        if (!res.ok) {
          return;
        }
        const data = (await res.json()) as ContextResponse;
        setState(data.state);
        const historyMessages = (data.history ?? [])
          .map((item, index) => ({
            id: `${item.timestamp || Date.now().toString()}-${index}`,
            role: item.role === "user" ? "user" : "assistant",
            text: item.text,
          }))
          .slice(-30);

        if (historyMessages.length > 0) {
          setMessages(historyMessages as Msg[]);
        } else {
          setMessages([
            {
              id: `m-${Date.now()}`,
              role: "assistant",
              text: data.greeting,
            },
          ]);
        }
      } finally {
        setLoading(false);
      }
    }
    void boot();
  }, []);

  const badge = useMemo(() => {
    if (!state) return "Loading";
    const bits = [shortMode(state.execution_mode)];
    if (state.copilot_mode_assigned) {
      bits.push(state.copilot_mode_assigned.toUpperCase());
    }
    bits.push(state.autonomous_enabled ? "AUTO-EXEC ON" : "AUTO-EXEC OFF");
    bits.push(state.scan_auto_mode ? "AUTO-SCAN ON" : "AUTO-SCAN OFF");
    return bits.join(" · ");
  }, [state]);

  async function sendMessage(confirm = false) {
    const text = input.trim();
    if (!text && !confirm) return;

    if (!confirm) {
      setMessages((prev) => [...prev, { id: `u-${Date.now()}`, role: "user", text }]);
      setInput("");
    }

    setSending(true);
    try {
      const trusted = await ensureHighTrust({ apiBase: API_BASE });
      if (!trusted) {
        setMessages((prev) => [
          ...prev,
          { id: `w-${Date.now()}`, role: "assistant", text: "Security verification was cancelled." },
        ]);
        return;
      }

      const res = await apiFetch(`${API_BASE}/copilot/chat`, {
        apiBase: API_BASE,
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: confirm ? "confirm" : text,
          confirm,
          pending_action: confirm ? pendingAction : null,
        }),
      });

      if (!res.ok) {
        setMessages((prev) => [
          ...prev,
          { id: `e-${Date.now()}`, role: "assistant", text: "I could not complete that action right now." },
        ]);
        return;
      }

      const data = (await res.json()) as ChatResponse;
      setState(data.state);
      setPendingAction(data.pending_action);
      const parserSuffix = data.parser_used ? ` (${data.parser_used})` : "";
      setMessages((prev) => [...prev, { id: `a-${Date.now()}`, role: "assistant", text: `${data.reply}${parserSuffix}` }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="fixed bottom-2 right-2 z-[70] w-[min(420px,calc(100vw-1rem))] sm:bottom-4 sm:right-4 sm:w-[min(420px,calc(100vw-2rem))]">
      <div className="rounded-xl border border-slate-700 bg-slate-900/95 shadow-2xl backdrop-blur">
        <button
          type="button"
          onClick={() => setOpen((v) => !v)}
          className="flex w-full items-center justify-between px-4 py-3 text-left"
        >
          <div>
            <div className="text-xs uppercase tracking-wider text-cyan-300">Dashboard Copilot</div>
            <div className="text-[11px] text-slate-400">{badge}</div>
          </div>
          <span className="text-slate-400">{open ? "−" : "+"}</span>
        </button>

        {open && (
          <div className="border-t border-slate-800 px-4 pb-4 pt-3">
            <div className="mb-3 max-h-64 space-y-2 overflow-y-auto pr-1">
              {loading ? <p className="text-xs text-slate-500">Loading copilot...</p> : null}
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={`rounded-lg px-3 py-2 text-xs ${
                    m.role === "assistant"
                      ? "border border-cyan-700/30 bg-cyan-900/20 text-cyan-100"
                      : "border border-slate-700 bg-slate-800/70 text-slate-100"
                  }`}
                >
                  {m.text}
                </div>
              ))}
            </div>

            <div className="flex gap-2">
              <input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    void sendMessage(false);
                  }
                }}
                placeholder="Tell me what to adjust..."
                className="flex-1 rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-xs text-slate-100 placeholder:text-slate-500"
              />
              <button
                type="button"
                disabled={sending}
                onClick={() => void sendMessage(false)}
                className="rounded-md bg-cyan-600 px-3 py-2 text-xs font-medium text-white disabled:opacity-50"
              >
                {sending ? "..." : "Send"}
              </button>
            </div>

            {pendingAction && (
              <div className="mt-3 flex items-center justify-between rounded-md border border-amber-700/40 bg-amber-900/20 px-3 py-2">
                <div className="text-[11px] text-amber-100">Action awaiting confirmation</div>
                <button
                  type="button"
                  disabled={sending}
                  onClick={() => void sendMessage(true)}
                  className="rounded border border-amber-500/60 px-2 py-1 text-[11px] text-amber-200 hover:bg-amber-500/10 disabled:opacity-50"
                >
                  Confirm
                </button>
              </div>
            )}

            {state && (
              <div className="mt-3 grid grid-cols-2 gap-2 text-[11px] text-slate-400">
                <div className="rounded border border-slate-800 px-2 py-1">Balance: ${state.account_balance.toLocaleString()}</div>
                <div className="rounded border border-slate-800 px-2 py-1">Cycles: {state.autonomous_cycles_run}</div>
                <div className="rounded border border-slate-800 px-2 py-1">Goal: {state.goal_enabled ? "ON" : "OFF"}</div>
                <div className="rounded border border-slate-800 px-2 py-1">
                  Target: {state.goal_target_capital ? `$${state.goal_target_capital.toLocaleString()}` : "-"}
                </div>
                <div className="rounded border border-slate-800 px-2 py-1">Daily risk: {(state.daily_loss_limit_pct * 100).toFixed(1)}%</div>
                <div className="rounded border border-slate-800 px-2 py-1">Max DD: {(state.max_drawdown_limit_pct * 100).toFixed(1)}%</div>
                <div className="col-span-2 rounded border border-slate-800 px-2 py-1">
                  Live-hours policy: {state.live_only_during_market_hours ? `ON (${state.market_open_hhmm}-${state.market_close_hhmm} ${state.market_timezone})` : "OFF"}
                </div>
              </div>
            )}

            <div className="mt-3 flex flex-wrap gap-2">
              {[
                "Enable autonomous execution",
                "Set daily risk to 2% and max drawdown to 10%",
                "Only run live during market hours",
                "I need an additional $5000 in 30 days",
                "$250 weekly for 12 weeks",
              ].map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => setInput(prompt)}
                  className="rounded border border-slate-700 px-2 py-1 text-[10px] text-slate-400 hover:border-slate-500 hover:text-slate-200"
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
