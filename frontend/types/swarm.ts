export type AgentAction = "BUY" | "SELL" | "HOLD";
export type MarketRegime = "TRENDING" | "RANGE_BOUND" | "HIGH_VOLATILITY";
export type ExecutionMode = "SIMULATION" | "PAPER_TRADING" | "LIVE_TRADING";

export type SwarmAgentSignal = {
  agent_name: string;
  action: AgentAction;
  confidence: number;
  reasoning: string;
};

export type SwarmCycleResponse = {
  cycle_id: string;
  request_id: string;
  symbol: string;
  timestamp: string;
  regime: MarketRegime;
  agent_signals: SwarmAgentSignal[];
  final_action: AgentAction;
  final_confidence: number;
  consensus_reasoning: string;
  execution_submitted: boolean;
  execution_result: Record<string, unknown> | null;
  vetoed: boolean;
  veto_reason: string;
  outcome: {
    entry_price: number;
    exit_price: number;
    pnl: number;
    outcome_label: "WIN" | "LOSS";
  } | null;
  agent_attribution: Array<{
    agent_name: string;
    prediction: AgentAction;
    confidence: number;
    correct: boolean | null;
    pnl_contribution: number | null;
  }>;
};

export type SwarmStatusResponse = {
  agents: Array<{ name: string; confidence_score: number }>;
  total_cycles: number;
  execution_mode: ExecutionMode;
  latest_decision: Record<string, unknown> | null;
};

export type SwarmDecisionListResponse = {
  decisions: SwarmCycleResponse[];
  total_cycles: number;
};

export type RunCycleRequest = {
  symbol: string;
  close_prices: number[];
  volumes: number[];
  regime: MarketRegime;
  regime_confidence: number;
  qty: number;
};

export type OutcomeUpdateRequest = {
  entry_price: number;
  exit_price: number;
};

// ---------------------------------------------------------------------------
// Dynamic Weight Engine types
// ---------------------------------------------------------------------------

export type AgentWeightEntry = {
  agent_name: string;
  weight: number;   // 0–1, normalised
  raw_score: number;
};

export type AgentWeightSnapshot = {
  cycle_id: string;
  timestamp: string;
  regime: MarketRegime;
  weights: AgentWeightEntry[];
};

export type AgentWeightsResponse = {
  regime_weights: Record<MarketRegime, AgentWeightEntry[]>;
};

export type AgentWeightHistoryResponse = {
  snapshots: AgentWeightSnapshot[];
  total_settled_cycles: number;
};
