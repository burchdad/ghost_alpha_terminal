"use client";

import { create } from "zustand";

import type {
  AgentWeightHistoryResponse,
  AgentWeightsResponse,
  ExecutionMode,
  OutcomeUpdateRequest,
  RunCycleRequest,
  SwarmCycleResponse,
  SwarmDecisionListResponse,
  SwarmStatusResponse,
} from "../types/swarm";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "/api";

type LiveTransport = "websocket" | "polling";

type SwarmStore = {
  loading: boolean;
  runningCycle: boolean;
  error: string | null;
  decisions: SwarmCycleResponse[];
  status: SwarmStatusResponse | null;
  totalCycles: number;
  transport: LiveTransport;
  websocketConnected: boolean;
  executionMode: ExecutionMode;
  lastUpdated: string | null;
  // Dynamic weight engine state
  regimeWeights: AgentWeightsResponse | null;
  weightHistory: AgentWeightHistoryResponse | null;
  fetchStatus: () => Promise<void>;
  fetchDecisions: (limit?: number) => Promise<void>;
  runCycle: (payload: RunCycleRequest) => Promise<SwarmCycleResponse | null>;
  setExecutionMode: (mode: ExecutionMode) => Promise<void>;
  updateOutcome: (cycleId: string, payload: OutcomeUpdateRequest) => Promise<SwarmCycleResponse | null>;
  fetchWeights: () => Promise<void>;
  startLive: () => void;
  stopLive: () => void;
};

let socket: WebSocket | null = null;
let pollHandle: ReturnType<typeof setInterval> | null = null;

function wsUrlFromApiBase(base: string): string | null {
  if (base.startsWith("/")) {
    return null;
  }
  if (base.startsWith("https://")) {
    return base.replace("https://", "wss://");
  }
  if (base.startsWith("http://")) {
    return base.replace("http://", "ws://");
  }
  return null;
}

function dedupeAndSort(records: SwarmCycleResponse[]): SwarmCycleResponse[] {
  const map = new Map<string, SwarmCycleResponse>();
  for (const item of records) {
    map.set(item.cycle_id, item);
  }
  return [...map.values()].sort((a, b) => Date.parse(b.timestamp) - Date.parse(a.timestamp));
}

export const useSwarmStore = create<SwarmStore>((set, get) => ({
  loading: false,
  runningCycle: false,
  error: null,
  decisions: [],
  status: null,
  totalCycles: 0,
  transport: "polling",
  websocketConnected: false,
  executionMode: "SIMULATION",
  lastUpdated: null,
  regimeWeights: null,
  weightHistory: null,

  fetchStatus: async () => {
    try {
      const res = await fetch(`${API_BASE}/agents/status`, { cache: "no-store" });
      if (!res.ok) {
        throw new Error(`Status request failed: HTTP ${res.status}`);
      }
      const data = (await res.json()) as SwarmStatusResponse;
      set({
        status: data,
        totalCycles: data.total_cycles,
        executionMode: data.execution_mode,
        error: null,
        lastUpdated: new Date().toISOString(),
      });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to load swarm status" });
    }
  },

  fetchDecisions: async (limit = 150) => {
    set({ loading: true });
    try {
      const res = await fetch(`${API_BASE}/agents/decisions?limit=${limit}`, { cache: "no-store" });
      if (!res.ok) {
        throw new Error(`Decisions request failed: HTTP ${res.status}`);
      }
      const data = (await res.json()) as SwarmDecisionListResponse;
      set({
        decisions: dedupeAndSort(data.decisions),
        totalCycles: data.total_cycles,
        loading: false,
        error: null,
        lastUpdated: new Date().toISOString(),
      });
    } catch (err) {
      set({
        loading: false,
        error: err instanceof Error ? err.message : "Failed to load decisions",
      });
    }
  },

  runCycle: async (payload: RunCycleRequest) => {
    set({ runningCycle: true });
    try {
      const res = await fetch(`${API_BASE}/agents/run-cycle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        throw new Error(`Run cycle failed: HTTP ${res.status}`);
      }
      const data = (await res.json()) as SwarmCycleResponse;
      set((state) => ({
        runningCycle: false,
        error: null,
        decisions: dedupeAndSort([data, ...state.decisions]),
        totalCycles: state.totalCycles + 1,
        lastUpdated: new Date().toISOString(),
      }));
      await get().fetchStatus();
      return data;
    } catch (err) {
      set({
        runningCycle: false,
        error: err instanceof Error ? err.message : "Failed to run cycle",
      });
      return null;
    }
  },

  setExecutionMode: async (mode) => {
    try {
      const res = await fetch(`${API_BASE}/agents/execution-mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      if (!res.ok) {
        throw new Error(`Execution mode update failed: HTTP ${res.status}`);
      }
      set({ executionMode: mode, error: null });
      await get().fetchStatus();
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to update execution mode" });
    }
  },

  updateOutcome: async (cycleId, payload) => {
    try {
      const res = await fetch(`${API_BASE}/agents/decisions/${cycleId}/outcome`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        throw new Error(`Outcome update failed: HTTP ${res.status}`);
      }
      const updated = (await res.json()) as SwarmCycleResponse;
      set((state) => ({
        decisions: dedupeAndSort([updated, ...state.decisions]),
        error: null,
        lastUpdated: new Date().toISOString(),
      }));
      return updated;
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to update cycle outcome" });
      return null;
    }
  },

  fetchWeights: async () => {
    try {
      const [weightsRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/agents/weights`, { cache: "no-store" }),
        fetch(`${API_BASE}/agents/weights/history?limit=100`, { cache: "no-store" }),
      ]);
      if (!weightsRes.ok || !historyRes.ok) {
        throw new Error("Failed to load agent weights");
      }
      const weights = (await weightsRes.json()) as AgentWeightsResponse;
      const history = (await historyRes.json()) as AgentWeightHistoryResponse;
      set({ regimeWeights: weights, weightHistory: history, error: null });
    } catch (err) {
      set({ error: err instanceof Error ? err.message : "Failed to fetch agent weights" });
    }
  },

  startLive: () => {
    get().stopLive();

    pollHandle = setInterval(() => {
      void get().fetchDecisions(150);
      void get().fetchStatus();
    }, 8000);

    const wsBase = wsUrlFromApiBase(API_BASE);
    if (!wsBase) {
      set({ websocketConnected: false, transport: "polling" });
      return;
    }

    const ws = new WebSocket(`${wsBase}/ws/agents/live`);
    socket = ws;

    ws.onopen = () => {
      set({ websocketConnected: true, transport: "websocket", error: null });
    };

    ws.onmessage = (event) => {
      try {
        const incoming = JSON.parse(event.data) as SwarmCycleResponse;
        set((state) => ({
          decisions: dedupeAndSort([incoming, ...state.decisions]),
          totalCycles: Math.max(state.totalCycles, state.decisions.length + 1),
          lastUpdated: new Date().toISOString(),
        }));
      } catch {
        // Ignore malformed frames.
      }
    };

    ws.onerror = () => {
      set({ websocketConnected: false, transport: "polling" });
    };

    ws.onclose = () => {
      set({ websocketConnected: false, transport: "polling" });
      socket = null;
    };
  },

  stopLive: () => {
    if (socket) {
      socket.close();
      socket = null;
    }
    if (pollHandle) {
      clearInterval(pollHandle);
      pollHandle = null;
    }
    set({ websocketConnected: false, transport: "polling" });
  },
}));
