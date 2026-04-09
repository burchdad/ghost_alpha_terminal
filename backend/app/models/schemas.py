from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Candle(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class ForecastResponse(BaseModel):
    symbol: str
    timeframe: str
    direction: Literal["UP", "DOWN", "SIDEWAYS"]
    confidence: float = Field(ge=0, le=1)
    volatility: Literal["LOW", "MEDIUM", "HIGH"]
    range_bound: bool
    forecast_prices: list[float]
    generated_at: datetime


class OptionContract(BaseModel):
    symbol: str
    strike: float
    expiration: str
    option_type: Literal["CALL", "PUT"]
    iv: float
    open_interest: int
    volume: int
    delta: float
    gamma: float
    theta: float
    vega: float


class OptionsChainResponse(BaseModel):
    symbol: str
    underlying_price: float
    contracts: list[OptionContract]
    avg_iv: float
    generated_at: datetime


class SignalResponse(BaseModel):
    symbol: str
    signal: str
    confidence: float = Field(ge=0, le=1)
    reasoning: str
    generated_at: datetime


class AgentPerformance(BaseModel):
    accuracy: float = Field(ge=0, le=1)
    win_rate: float = Field(ge=0, le=1)
    avg_return: float
    confidence_calibration: float = Field(ge=0)
    composite_score: float = Field(ge=0, le=1)


class AgentDecision(BaseModel):
    agent_name: str
    bias: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    confidence: float = Field(ge=0, le=1)
    raw_confidence: float | None = Field(default=None, ge=0, le=1)
    adjusted_confidence: float | None = Field(default=None, ge=0, le=1)
    suggested_strategy: str
    reasoning: str
    performance: AgentPerformance | None = None
    weighted_confidence: float | None = Field(default=None, ge=0, le=1)


class ConsensusDecision(BaseModel):
    final_bias: Literal["BULLISH", "BEARISH", "NEUTRAL"]
    confidence: float = Field(ge=0, le=1)
    top_strategy: str


class RegimeResponse(BaseModel):
    regime: Literal["TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY"]
    confidence: float = Field(ge=0, le=1)


class SwarmResponse(BaseModel):
    symbol: str
    regime: Literal["TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY"] = "RANGE_BOUND"
    regime_confidence: float = Field(default=0.5, ge=0, le=1)
    consensus: ConsensusDecision
    agent_breakdown: list[AgentDecision]
    recommended_trade: str
    position_size: float = 0
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    expected_value: float = 0
    generated_at: datetime


class TradeOutcomeRequest(BaseModel):
    symbol: str
    strategy: str
    regime: Literal["TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY"] | None = None
    entry_price: float = Field(gt=0)
    exit_price: float = Field(gt=0)


class TradeOutcomeResponse(BaseModel):
    symbol: str
    strategy: str
    regime: Literal["TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY"]
    entry_price: float
    exit_price: float
    pnl: float
    outcome: Literal["WIN", "LOSS"]
    timestamp: datetime


class AgentPerformanceRow(BaseModel):
    agent_name: str
    accuracy: float = Field(ge=0, le=1)
    win_rate: float = Field(ge=0, le=1)
    avg_return: float
    confidence_calibration: float = Field(ge=0)
    composite_score: float = Field(ge=0, le=1)


class StrategyPerformanceRow(BaseModel):
    strategy: str
    trades: int = Field(ge=0)
    win_rate: float = Field(ge=0, le=1)
    avg_pnl: float


class PerformanceResponse(BaseModel):
    symbol: str
    best_agent: str
    agent_leaderboard: list[AgentPerformanceRow]
    top_strategies: list[StrategyPerformanceRow]
    by_regime: dict[str, dict[str, float | int]]
    generated_at: datetime


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "1d"
    start_date: datetime
    end_date: datetime
    initial_capital: float = Field(default=100000, gt=1000)
    risk_per_trade: float = Field(default=0.01, gt=0, le=0.05)
    take_profit_pct: float = Field(default=0.03, gt=0, le=0.5)
    stop_loss_pct: float = Field(default=0.02, gt=0, le=0.5)
    max_hold_periods: int = Field(default=5, ge=1, le=50)


class SimulatedTrade(BaseModel):
    entry_time: datetime
    exit_time: datetime
    side: Literal["LONG", "SHORT"]
    strategy: str
    entry_price: float
    exit_price: float
    pnl: float
    return_pct: float
    outcome: Literal["WIN", "LOSS"]


class EquityPoint(BaseModel):
    timestamp: datetime
    equity: float


class BacktestResponse(BaseModel):
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    starting_capital: float
    ending_balance: float
    total_trades: int
    win_rate: float = Field(ge=0, le=1)
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    equity_curve: list[EquityPoint]
    trade_history: list[SimulatedTrade]


class ExecuteTradeRequest(BaseModel):
    symbol: str
    strategy: str
    side: Literal["LONG", "SHORT"]
    entry_price: float = Field(gt=0)
    stop_loss_pct: float = Field(default=0.02, gt=0, le=0.5)
    take_profit_pct: float = Field(default=0.03, gt=0, le=0.5)
    account_balance: float = Field(default=100000, gt=1000)
    risk_per_trade: float = Field(default=0.01, gt=0, le=0.05)
    confidence: float = Field(default=0.6, ge=0, le=1)


class ExecuteTradeResponse(BaseModel):
    accepted: bool
    reason: str | None = None
    position_size: float = 0
    max_loss_amount: float = 0
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "HIGH"
    expected_value: float = 0
    risk_reward_ratio: float = 0
    target_pct: float = 0
    position_notional: float = 0


class ActivePosition(BaseModel):
    symbol: str
    strategy: str
    side: str
    entry_price: float
    units: float
    notional: float
    sector: str
    opened_at: datetime


class PortfolioResponse(BaseModel):
    account_balance: float
    active_positions: list[ActivePosition]
    total_exposure: float
    risk_exposure_pct: float
    sector_concentration: dict[str, float]
    strategy_exposure: dict[str, float]
    available_buying_power: float
    max_concurrent_trades: int


class RejectedTradeLog(BaseModel):
    timestamp: datetime
    symbol: str
    reason: str


class ControlStatusResponse(BaseModel):
    trading_enabled: bool
    system_status: Literal["ACTIVE", "PAUSED"]
    mode: Literal["SAFE", "NORMAL"]
    daily_pnl: float
    daily_loss: float
    daily_loss_limit: float
    rolling_drawdown: float
    rolling_drawdown_pct: float
    max_drawdown_limit_pct: float
    rejected_trades: list[RejectedTradeLog]
    autonomous_enabled: bool = False
    autonomous_interval_seconds: int = 300
    autonomous_symbols: list[str] = []
    autonomous_cycles_run: int = 0
    autonomous_last_run_at: datetime | None = None
    autonomous_last_error: str | None = None


class KillSwitchUpdateRequest(BaseModel):
    trading_enabled: bool


class KillSwitchUpdateResponse(BaseModel):
    trading_enabled: bool
    system_status: Literal["ACTIVE", "PAUSED"]


# ---------------------------------------------------------------------------
# Alpaca Request ID tracking
# ---------------------------------------------------------------------------

class AlpacaRequestIdEntry(BaseModel):
    alpaca_request_id: str
    endpoint: str
    method: str
    status_code: int
    timestamp: datetime
    symbol: str | None = None


class AlpacaRequestIdsResponse(BaseModel):
    recent: list[AlpacaRequestIdEntry]
    total_captured: int


class AlpacaAccountPnlResponse(BaseModel):
    equity: float
    last_equity: float
    balance_change: float


class AlpacaOrderRequest(BaseModel):
    symbol: str
    side: Literal["buy", "sell"]
    type: Literal["market", "limit", "stop", "stop_limit", "trailing_stop"] = "market"
    time_in_force: Literal["day", "gtc", "opg", "cls", "ioc", "fok"] = "day"
    qty: str | None = None
    notional: str | None = None
    limit_price: str | None = None
    stop_price: str | None = None
    trail_price: str | None = None
    trail_percent: str | None = None
    order_class: Literal["simple", "bracket", "oco", "oto"] | None = None
    take_profit: dict | None = None
    stop_loss: dict | None = None
    client_order_id: str | None = None
    extended_hours: bool | None = None


class AlpacaAssetsQuery(BaseModel):
    status: Literal["active", "inactive"] = "active"
    asset_class: Literal["us_equity", "crypto"] = "us_equity"


# ---------------------------------------------------------------------------
# Agent Swarm Layer schemas
# ---------------------------------------------------------------------------

class SwarmAgentSignal(BaseModel):
    agent_name: str
    action: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(ge=0, le=1)
    reasoning: str


class AgentAttribution(BaseModel):
    agent_name: str
    prediction: Literal["BUY", "SELL", "HOLD"]
    confidence: float = Field(ge=0, le=1)
    correct: bool | None = None
    pnl_contribution: float | None = None


class DecisionOutcome(BaseModel):
    entry_price: float = Field(gt=0)
    exit_price: float = Field(gt=0)
    pnl: float
    outcome_label: Literal["WIN", "LOSS"]


class SwarmCycleRequest(BaseModel):
    symbol: str
    close_prices: list[float] = Field(min_length=2)
    volumes: list[float] = Field(min_length=1)
    regime: Literal["TRENDING", "RANGE_BOUND", "HIGH_VOLATILITY"] = "RANGE_BOUND"
    regime_confidence: float = Field(default=0.5, ge=0, le=1)
    qty: float = Field(default=1.0, gt=0)


class SwarmCycleResponse(BaseModel):
    cycle_id: str
    request_id: str = ""
    symbol: str
    timestamp: datetime
    regime: str
    agent_signals: list[SwarmAgentSignal]
    final_action: Literal["BUY", "SELL", "HOLD"]
    final_confidence: float = Field(ge=0, le=1)
    consensus_reasoning: str
    execution_submitted: bool
    execution_result: dict | None = None
    vetoed: bool
    veto_reason: str
    allocation: AllocationDecision | None = None
    outcome: DecisionOutcome | None = None
    agent_attribution: list[AgentAttribution] = []


class SwarmStatusResponse(BaseModel):
    agents: list[dict]         # {name, confidence_score}
    total_cycles: int
    execution_mode: Literal["SIMULATION", "PAPER_TRADING", "LIVE_TRADING"]
    current_weights: dict[str, dict[str, float]] | None = None
    latest_decision: dict | None = None


class SwarmDecisionListResponse(BaseModel):
    decisions: list[SwarmCycleResponse]
    total_cycles: int


class DecisionOutcomeUpdateRequest(BaseModel):
    entry_price: float = Field(gt=0)
    exit_price: float = Field(gt=0)


class ExecutionModeUpdateRequest(BaseModel):
    mode: Literal["SIMULATION", "PAPER_TRADING", "LIVE_TRADING"]


class ExecutionModeResponse(BaseModel):
    mode: Literal["SIMULATION", "PAPER_TRADING", "LIVE_TRADING"]


# ---------------------------------------------------------------------------
# Dynamic Weight Engine schemas
# ---------------------------------------------------------------------------

class AgentWeightEntry(BaseModel):
    agent_name: str
    weight: float = Field(ge=0, le=1)
    raw_score: float


class AgentWeightSnapshot(BaseModel):
    cycle_id: str
    timestamp: datetime
    regime: str
    weights: list[AgentWeightEntry]


class AgentWeightsResponse(BaseModel):
    """Current weights for all agents across all regimes."""
    regime_weights: dict[str, list[AgentWeightEntry]]
    # e.g. {"TRENDING": [{agent_name, weight, raw_score}, ...], ...}


class AgentWeightHistoryResponse(BaseModel):
    snapshots: list[AgentWeightSnapshot]
    total_settled_cycles: int


class AllocationDecision(BaseModel):
    accepted: bool
    target_pct: float = Field(ge=0, le=1)
    recommended_notional: float
    recommended_qty: float
    max_risk_amount: float
    stop_loss_pct: float
    agent_agreement: float = Field(ge=0, le=1)
    rationale: list[str]
    reason: str


class ExecutionHistoryEntry(BaseModel):
    execution_id: str
    cycle_id: str
    symbol: str
    regime: str
    action: str
    strategy: str
    confidence: float
    risk_level: str
    allocation_pct: float
    qty: float
    notional: float
    mode: str
    submitted: bool
    order_id: str | None = None
    reason: str
    error: str | None = None
    timestamp: datetime
    outcome_label: str | None = None
    pnl: float | None = None


class ExecutionHistoryResponse(BaseModel):
    executions: list[ExecutionHistoryEntry]


class AutonomousModeUpdateRequest(BaseModel):
    enabled: bool | None = None
    interval_seconds: int | None = Field(default=None, ge=60, le=3600)
    symbols: list[str] | None = None


class AutonomousModeStatusResponse(BaseModel):
    enabled: bool
    interval_seconds: int
    symbols: list[str]
    last_run_at: datetime | None = None
    last_error: str | None = None
    cycles_run: int = 0
