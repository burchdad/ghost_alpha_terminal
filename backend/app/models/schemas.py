from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


OptionsStrategyType = Literal[
    "LONG_CALL",
    "LONG_PUT",
    "VERTICAL_CALL",
    "VERTICAL_PUT",
    "CALENDAR_CALL",
    "CALENDAR_PUT",
    "DIAGONAL_CALL",
    "DIAGONAL_PUT",
    "RATIO_CALL",
    "RATIO_PUT",
    "BUTTERFLY_CALL",
    "BUTTERFLY_PUT",
    "CONDOR_CALL",
    "CONDOR_PUT",
    "IRON_CONDOR",
    "STRADDLE",
    "STRANGLE",
    "COVERED_CALL",
    "COVERED_PUT",
    "PROTECTIVE_CALL",
    "PROTECTIVE_PUT",
    "CUSTOM_2_LEG",
    "CUSTOM_3_LEG",
    "CUSTOM_4_LEG",
    "CUSTOM_STOCK_OPTION",
]


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
    option_symbol: str | None = None
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
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    mid: float | None = None
    underlying: str | None = None
    source: Literal["tradier", "synthetic"] = "synthetic"


class OptionsChainResponse(BaseModel):
    symbol: str
    underlying_price: float
    contracts: list[OptionContract]
    avg_iv: float
    source: Literal["tradier", "synthetic"] = "synthetic"
    selected_expiration: str | None = None
    available_expirations: list[str] = []
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
    explainability: dict | None = None
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
    enable_evolution: bool = True
    enable_compounding: bool = True


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
    stability_score: float = 0.0
    equity_curve: list[EquityPoint]
    trade_history: list[SimulatedTrade]


class ControlledExperimentRun(BaseModel):
    label: str
    enable_evolution: bool
    enable_compounding: bool
    total_trades: int
    win_rate: float = Field(ge=0, le=1)
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    stability_score: float
    ending_balance: float


class ControlledExperimentComparison(BaseModel):
    metric: Literal["win_rate", "total_pnl", "max_drawdown", "stability_score"]
    mode_a_label: str
    mode_b_label: str
    mode_a_value: float
    mode_b_value: float
    delta_b_minus_a: float


class ControlledExperimentResponse(BaseModel):
    symbol: str
    timeframe: str
    start_date: datetime
    end_date: datetime
    runs: list[ControlledExperimentRun]
    comparisons: list[ControlledExperimentComparison]
    recommended_mode: str
    control_mode: str
    promotion_applied: bool
    promotion_reason: str
    live_mode: dict


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
    governor_decision: str | None = None
    governor_reason: str | None = None
    explainability: dict | None = None


class OptionsRiskAssessmentResponse(BaseModel):
    approved: bool
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    risk_reward_ratio: float
    expected_value: float
    max_loss_amount: float
    max_profit_amount: float | None = None
    max_loss_pct_of_balance: float
    spread_pct: float
    contracts: int
    contract_cost: float
    stop_loss_pct: float
    take_profit_pct: float
    reason: str = ""
    warnings: list[str] = Field(default_factory=list)


class TradierOptionOrderRequest(BaseModel):
    underlying: str = Field(min_length=1, max_length=32)
    option_symbol: str = Field(min_length=8, max_length=64)
    side: Literal["buy_to_open", "buy_to_close", "sell_to_open", "sell_to_close"]
    quantity: int = Field(gt=0, le=1000)
    order_type: Literal["market", "limit", "stop", "stop_limit"] = "limit"
    duration: Literal["day", "gtc"] = "day"
    price: float | None = Field(default=None, gt=0)
    stop: float | None = Field(default=None, gt=0)
    preview: bool = False
    tag: str | None = Field(default=None, max_length=64)


class OptionsStrategyLegRequest(BaseModel):
    instrument: Literal["option", "equity"] = "option"
    option_symbol: str | None = Field(default=None, min_length=8, max_length=64)
    option_type: Literal["CALL", "PUT"] | None = None
    action: Literal[
        "buy",
        "sell",
        "buy_to_open",
        "buy_to_close",
        "sell_to_open",
        "sell_to_close",
    ]
    strike: float | None = Field(default=None, gt=0)
    expiration: str | None = None
    quantity_ratio: int = Field(default=1, ge=1, le=10)
    shares: int | None = Field(default=None, gt=0, le=100000)


class OptionsStrategyLegResponse(BaseModel):
    instrument: Literal["option", "equity"]
    action: str
    ratio: int
    quantity: int
    shares: int | None = None
    option_symbol: str | None = None
    option_type: Literal["CALL", "PUT"] | None = None
    strike: float | None = None
    expiration: str | None = None
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    mid: float | None = None
    estimated_leg_value: float | None = None
    source: Literal["tradier", "synthetic", "manual"] = "manual"


class TradierStrategyOrderRequest(BaseModel):
    underlying: str = Field(min_length=1, max_length=32)
    strategy: OptionsStrategyType
    order_class: Literal["option", "multileg", "combo"]
    order_type: Literal["market", "limit", "stop", "stop_limit", "debit", "credit", "even"]
    duration: Literal["day", "gtc"] = "day"
    quantity: int = Field(gt=0, le=1000)
    price: float | None = Field(default=None, gt=0)
    stop: float | None = Field(default=None, gt=0)
    preview: bool = True
    tag: str | None = Field(default=None, max_length=64)
    legs: list[OptionsStrategyLegRequest] = Field(default_factory=list, min_length=1, max_length=4)


class OptionsExecutionRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    strategy: OptionsStrategyType | None = None
    bias: Literal["BULLISH", "BEARISH", "NEUTRAL"] = "BULLISH"
    quantity: int = Field(default=1, gt=0, le=100)
    expiration: str | None = None
    secondary_expiration: str | None = None
    width: float | None = Field(default=None, gt=0)
    wing_width: float | None = Field(default=None, gt=0)
    target_delta: float | None = Field(default=None, gt=0, le=1)
    target_otm_pct: float | None = Field(default=0.03, gt=0, le=0.25)
    max_contract_cost: float | None = Field(default=None, gt=0)
    min_open_interest: int = Field(default=100, ge=0)
    min_volume: int = Field(default=10, ge=0)
    max_spread_pct: float = Field(default=0.20, gt=0, le=1)
    preview: bool = True
    account_balance: float = Field(default=100000, gt=1000)
    confidence: float = Field(default=0.6, ge=0, le=1)
    custom_legs: list[OptionsStrategyLegRequest] = Field(default_factory=list, max_length=4)


class OptionsExecutionResponse(BaseModel):
    approved: bool
    provider: str = "tradier"
    symbol: str
    strategy: OptionsStrategyType | None = None
    order_class: Literal["option", "multileg", "combo"] | None = None
    option_symbol: str | None = None
    side: str | None = None
    quantity: int = 0
    expiration: str | None = None
    secondary_expiration: str | None = None
    bid: float | None = None
    ask: float | None = None
    last: float | None = None
    mid: float | None = None
    estimated_cost: float | None = None
    estimated_net_debit: float | None = None
    estimated_net_credit: float | None = None
    order_preview: bool = True
    order_response: dict | None = None
    risk: OptionsRiskAssessmentResponse | None = None
    legs: list[OptionsStrategyLegResponse] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    reason: str = ""


class ActivePosition(BaseModel):
    symbol: str
    strategy: str
    side: str
    entry_price: float
    current_price: float = 0.0
    unrealized_pnl: float = 0.0
    unrealized_pnl_pct: float = 0.0
    units: float
    notional: float
    sector: str
    opened_at: datetime


class BrokerAccountSnapshot(BaseModel):
    broker: str
    account_label: str
    account_mode: str
    connected: bool
    account_balance: float | None = None
    buying_power: float | None = None
    currency: str = "USD"
    last_error: str | None = None


class PortfolioResponse(BaseModel):
    account_balance: float
    active_positions: list[ActivePosition]
    total_exposure: float
    risk_exposure_pct: float
    sector_concentration: dict[str, float]
    strategy_exposure: dict[str, float]
    available_buying_power: float
    max_concurrent_trades: int
    broker_accounts: list[BrokerAccountSnapshot] = []


class RejectedTradeLog(BaseModel):
    timestamp: datetime
    symbol: str
    reason: str


class OptionsSprintStatusResponse(BaseModel):
    enabled: bool = False
    profile: str = "high_volume_directional"
    target_amount: float | None = None
    timeframe_days: int | None = None
    objective_summary: str | None = None
    activation_source: str = "manual"
    acknowledged_high_risk: bool = False
    allow_live_execution: bool = False
    live_execution_ready: bool = False
    live_execution_blockers: list[str] = []
    recommended_execution_mode: Literal["SIMULATION", "PAPER_TRADING", "LIVE_TRADING"] = "SIMULATION"
    strategy_bias: dict[str, float] = {}
    updated_at: datetime | None = None


class ControlStatusResponse(BaseModel):
    trading_enabled: bool
    system_status: Literal["ACTIVE", "PAUSED"]
    mode: Literal["SAFE", "NORMAL"]
    daily_pnl: float
    daily_loss: float
    daily_loss_limit: float
    daily_loss_limit_pct: float = 0.05
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
    options_sprint: OptionsSprintStatusResponse = Field(default_factory=OptionsSprintStatusResponse)


class KillSwitchUpdateRequest(BaseModel):
    trading_enabled: bool


class KillSwitchUpdateResponse(BaseModel):
    trading_enabled: bool
    system_status: Literal["ACTIVE", "PAUSED"]


class RiskLimitUpdateRequest(BaseModel):
    daily_loss_limit_pct: float = Field(default=0.05, gt=0, le=0.5)
    max_drawdown_limit_pct: float = Field(default=0.10, gt=0, le=0.5)


class RiskLimitUpdateResponse(BaseModel):
    daily_loss_limit_pct: float
    max_drawdown_limit_pct: float
    daily_loss_limit: float


class OptionsSprintUpdateRequest(BaseModel):
    enabled: bool = True
    target_amount: float | None = Field(default=None, gt=0)
    timeframe_days: int | None = Field(default=None, ge=1, le=3650)
    objective_summary: str | None = Field(default=None, max_length=500)
    activation_source: str = Field(default="manual", min_length=1, max_length=64)
    acknowledged_high_risk: bool = False
    allow_live_execution: bool = False


class PriceBar(BaseModel):
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float


class PriceHistoryResponse(BaseModel):
    symbol: str
    timeframe: str
    bars: list[PriceBar]
    source: str = "alpaca"


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


class AlpacaWithdrawalRequest(BaseModel):
    amount: float = Field(gt=0)
    destination: str = Field(min_length=2, max_length=64)
    memo: str | None = Field(default=None, max_length=255)


class AlpacaWithdrawalResponse(BaseModel):
    provider: str = "alpaca"
    status: Literal["PENDING", "SUBMITTED"]
    transfer_id: str | None = None
    amount: float
    destination: str
    requested_at: datetime
    hold_until: datetime | None = None
    hold_reasons: list[str] = []
    requires_confirmation: bool = False
    risk_score: int = 0
    risk_rating: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "LOW"
    risk_components: dict[str, int] = {}
    approval_id: int | None = None


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
    governor_decision: str | None = None
    governor_reason: str | None = None
    explainability: dict | None = None
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


class BrokerCapabilitiesResponse(BaseModel):
    capabilities: dict[str, dict]


class BrokerConnectionEntryResponse(BaseModel):
    provider: str
    label: str
    connected: bool
    configured: bool = False
    planned: bool = False
    connectable: bool
    disconnect_supported: bool
    auth_type: Literal["oauth", "api_key", "unavailable", "planned"]
    permissions: str
    mode: str | None = None
    status_label: str
    connect_path: str | None = None
    disconnect_path: str | None = None
    updated_at: datetime | None = None
    last_error: str | None = None
    notes: str | None = None
    oauth_url: str | None = None
    capabilities: dict[str, bool]


class BrokerConnectionsResponse(BaseModel):
    brokers: list[BrokerConnectionEntryResponse]


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
    realized_volatility_pct: float | None = Field(default=None, ge=0, le=1)
    kelly_fraction: float | None = Field(default=None, ge=0, le=1)
    goal_pressure_multiplier: float | None = Field(default=None, ge=0.5, le=2.5)
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


class GoalTargetRequest(BaseModel):
    start_capital: float = Field(gt=0)
    target_capital: float = Field(gt=0)
    timeframe_days: int = Field(ge=1, le=3650)


class GoalMissionRequest(BaseModel):
    target_capital: float = Field(gt=0)
    timeframe_days: int = Field(ge=1, le=3650)
    start_capital: float | None = Field(default=None, gt=0)
    execution_mode: Literal["SIMULATION", "PAPER_TRADING", "LIVE_TRADING"] | None = None
    interval_seconds: int = Field(default=300, ge=60, le=3600)
    symbols: list[str] | None = None
    trading_enabled: bool = True
    autonomous_enabled: bool = True
    trigger_initial_cycle: bool = True


class GoalMissionResponse(BaseModel):
    message: str
    execution_mode: Literal["SIMULATION", "PAPER_TRADING", "LIVE_TRADING"]
    trading_enabled: bool
    goal: dict
    autonomous: dict


class GoalStatusResponse(BaseModel):
    enabled: bool
    start_capital: float | None = None
    target_capital: float | None = None
    timeframe_days: int | None = None
    elapsed_days: float = 0
    remaining_days: float | None = None
    required_total_return: float = 0
    required_daily_return: float = 0
    required_daily_return_remaining: float = 0
    trajectory_expected_capital: float | None = None
    trajectory_gap_pct: float = 0
    goal_pressure_multiplier: float = 1.0
    success_probability: float = Field(default=0.5, ge=0, le=1)
    stress_level: Literal["LOW", "MEDIUM", "HIGH", "EXTREME"] = "LOW"
    target_unrealistic: bool = False
    suggested_target_capital: float | None = None
    suggested_timeframe_days: int | None = None
    message: str = ""


class OpportunityRecommendation(BaseModel):
    symbol: str
    asset_class: str
    region: str
    regime: str
    regime_confidence: float
    signal: str
    recommended_trade: str
    consensus_bias: str
    consensus_confidence: float
    expected_return_pct: float
    sentiment_score: float
    news_momentum_score: float
    event_strength: float
    data_classification: Literal["PUBLIC", "DERIVED", "RESTRICTED", "UNKNOWN"]
    sources_used: list[str]
    event_flags: list[str]
    context_modifiers: dict | None = None
    signal_validation: dict | None = None
    market_reaction: dict | None = None
    risk_level: str
    expected_value: float
    target_pct: float
    recommended_notional: float
    recommended_qty: float
    goal_pressure_multiplier: float
    realized_volatility_pct: float
    avg_dollar_volume: float
    spread_proxy: float
    prefilter_score: float
    tradable: bool
    risk_adjusted_score: float
    opportunity_score: float
    explainability: dict | None = None


class CapitalSplitRecommendation(BaseModel):
    symbol: str
    recommended_notional: float
    allocation_weight: float


class OpportunitiesResponse(BaseModel):
    scanned: int
    passed_prefilter: int
    opportunities: list[OpportunityRecommendation]
    capital_allocation_recommendations: list[CapitalSplitRecommendation]
    goal: GoalStatusResponse


class NewsSignalResponse(BaseModel):
    symbol: str
    timestamp: datetime
    data_classification: Literal["PUBLIC", "DERIVED", "RESTRICTED", "UNKNOWN"]
    sources_used: list[str]
    sentiment_score: float
    news_momentum_score: float
    event_strength: float
    event_flags: list[str]
    rationale: str


class NewsAuditEntryResponse(BaseModel):
    timestamp: datetime
    symbol: str
    data_classification: Literal["PUBLIC", "DERIVED", "RESTRICTED", "UNKNOWN"]
    sources_used: list[str]
    sentiment_score: float
    news_momentum_score: float
    event_strength: float
    event_flags: list[str]


class NewsAuditResponse(BaseModel):
    entries: list[NewsAuditEntryResponse]


class NewsSourceWhitelistResponse(BaseModel):
    sources: list[str]


class ContextModifiersResponse(BaseModel):
    confidence_modifier: float
    risk_modifier: float
    opportunity_boost: float


class ContextSignalResponse(BaseModel):
    symbol: str
    data_classification: Literal["PUBLIC", "DERIVED", "RESTRICTED", "UNKNOWN"]
    sources_used: list[str]
    sentiment_score: float
    news_momentum_score: float
    event_strength: float
    event_flags: list[str]
    signal_validation: dict
    market_reaction: dict
    modifiers: ContextModifiersResponse
    rationale: str


class DecisionAuditSummaryResponse(BaseModel):
    audit_id: str
    timestamp: datetime
    decision_type: str
    symbol: str
    status: str
    cycle_id: str | None = None


class DecisionAuditSummaryListResponse(BaseModel):
    entries: list[DecisionAuditSummaryResponse]


class DecisionAuditDetailResponse(BaseModel):
    audit_id: str
    timestamp: datetime
    decision_type: str
    symbol: str
    status: str
    cycle_id: str | None = None
    goal_snapshot: dict
    context_snapshot: dict
    allocation_snapshot: dict
    governor_snapshot: dict
    execution_snapshot: dict
    explainability_snapshot: dict


class DecisionReplayStepResponse(BaseModel):
    stage: str
    title: str
    summary: str
    payload: dict


class DecisionReplayResponse(BaseModel):
    audit_id: str
    symbol: str
    decision_type: str
    status: str
    generated_at: datetime
    replay_steps: list[DecisionReplayStepResponse]
    why_not: list[str] = []


# ---------------------------------------------------------------------------
# GhostAlpha Intelligence Engine — Orchestrator schemas
# ---------------------------------------------------------------------------

class OrchestratorCandidateItem(BaseModel):
    rank: int
    symbol: str
    asset_class: str
    region: str
    composite_score: float
    strategy_type: Literal["OPTIONS_PLAY", "SWING_TRADE", "DAY_TRADE", "SCALP", "WATCH", "IGNORE"]
    action_label: Literal["EXECUTE", "SIMULATE", "MONITOR", "SKIP"]
    regime: str
    consensus_bias: str
    consensus_confidence: float
    momentum_score: float
    volume_spike: float
    news_strength: float
    volatility: float
    expected_return_pct: float
    risk_level: str
    tradable: bool
    reasoning: str
    why_trade_exists: dict | None = None


class OrchestratorScanResponse(BaseModel):
    candidates: list[OrchestratorCandidateItem]
    market_narrative: str
    regime_summary: dict[str, int]
    sector_leaders: list[str]
    scanned_at: datetime
    scan_count: int
    total_scanned: int
    passed_prefilter: int
    auto_mode: bool


class OrchestratorStatusResponse(BaseModel):
    auto_mode: bool
    auto_interval_seconds: int
    scan_count: int
    last_scan_at: str | None = None
    top_pick: dict | None = None


class OrchestratorModeRequest(BaseModel):
    auto_mode: bool
    interval_seconds: int | None = Field(default=None, ge=60, le=3600)


class OrchestratorModeResponse(BaseModel):
    auto_mode: bool
    auto_interval_seconds: int
    scan_count: int
    last_scan_at: str | None = None
    top_pick: dict | None = None
