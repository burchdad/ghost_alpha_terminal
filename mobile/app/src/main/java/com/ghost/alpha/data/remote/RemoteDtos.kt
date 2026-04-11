package com.ghost.alpha.data.remote

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class LoginRequestDto(
    val email: String,
    val password: String
)

@JsonClass(generateAdapter = true)
data class UserDto(
    val id: String? = null,
    val email: String? = null,
    @Json(name = "full_name") val fullName: String? = null,
    @Json(name = "twofa_verified") val twoFaVerified: Boolean? = null,
    @Json(name = "twofa_method") val twoFaMethod: String? = null,
    @Json(name = "step_up_required") val stepUpRequired: Boolean? = null,
    @Json(name = "risk_score") val riskScore: Int? = null,
    @Json(name = "risk_reasons") val riskReasons: List<String>? = null
)

@JsonClass(generateAdapter = true)
data class AuthResponseDto(
    val user: UserDto? = null,
    @Json(name = "access_token") val accessToken: String? = null,
    @Json(name = "refresh_token") val refreshToken: String? = null,
    @Json(name = "token_type") val tokenType: String? = null,
    @Json(name = "access_token_expires_at") val accessTokenExpiresAt: String? = null,
    @Json(name = "refresh_token_expires_at") val refreshTokenExpiresAt: String? = null,
    @Json(name = "requires_2fa") val requiresTwoFactor: Boolean? = null,
    @Json(name = "challenge_method") val challengeMethod: String? = null
)

@JsonClass(generateAdapter = true)
data class TwoFactorVerifyRequestDto(
    val code: String,
    @Json(name = "trustDevice") val trustDevice: Boolean
)

@JsonClass(generateAdapter = true)
data class TwoFactorVerifyResponseDto(
    val success: Boolean,
    @Json(name = "high_trust_until") val highTrustUntil: String? = null,
    val method: String? = null,
    @Json(name = "trusted_device") val trustedDevice: Boolean = false
)

@JsonClass(generateAdapter = true)
data class HighTrustStatusDto(
    @Json(name = "high_trust") val highTrust: Boolean,
    @Json(name = "expires_at") val expiresAt: String? = null,
    @Json(name = "step_up_required") val stepUpRequired: Boolean = false,
    @Json(name = "risk_score") val riskScore: Int = 0,
    @Json(name = "risk_reasons") val riskReasons: List<String> = emptyList()
)

@JsonClass(generateAdapter = true)
data class SignalDto(
    val symbol: String,
    val signal: String,
    val confidence: Double,
    val reasoning: String,
    @Json(name = "generated_at") val generatedAt: String
)

@JsonClass(generateAdapter = true)
data class PositionDto(
    val symbol: String,
    val strategy: String = "live",
    val side: String,
    @Json(name = "entry_price") val entryPrice: Double,
    @Json(name = "current_price") val currentPrice: Double = 0.0,
    @Json(name = "unrealized_pnl") val unrealizedPnl: Double = 0.0,
    @Json(name = "unrealized_pnl_pct") val unrealizedPnlPct: Double = 0.0,
    val units: Double,
    val notional: Double,
    val sector: String = "Unknown",
    @Json(name = "opened_at") val openedAt: String
)

@JsonClass(generateAdapter = true)
data class PortfolioDto(
    @Json(name = "account_balance") val accountBalance: Double,
    @Json(name = "active_positions") val activePositions: List<PositionDto>,
    @Json(name = "total_exposure") val totalExposure: Double,
    @Json(name = "risk_exposure_pct") val riskExposurePct: Double,
    @Json(name = "available_buying_power") val availableBuyingPower: Double,
    @Json(name = "max_concurrent_trades") val maxConcurrentTrades: Int
)

@JsonClass(generateAdapter = true)
data class AgentDecisionDto(
    @Json(name = "agent_name") val agentName: String,
    val bias: String,
    val confidence: Double,
    val reasoning: String,
    @Json(name = "weighted_confidence") val weightedConfidence: Double? = null
)

@JsonClass(generateAdapter = true)
data class ConsensusDto(
    @Json(name = "final_bias") val finalBias: String,
    val confidence: Double,
    @Json(name = "top_strategy") val topStrategy: String
)

@JsonClass(generateAdapter = true)
data class SwarmResponseDto(
    val symbol: String,
    val regime: String,
    @Json(name = "regime_confidence") val regimeConfidence: Double,
    val consensus: ConsensusDto,
    @Json(name = "agent_breakdown") val agentBreakdown: List<AgentDecisionDto>,
    @Json(name = "risk_level") val riskLevel: String,
    @Json(name = "expected_value") val expectedValue: Double,
    @Json(name = "generated_at") val generatedAt: String
)

@JsonClass(generateAdapter = true)
data class ExecuteTradeRequestDto(
    val symbol: String,
    val strategy: String,
    val side: String,
    @Json(name = "entry_price") val entryPrice: Double,
    @Json(name = "stop_loss_pct") val stopLossPct: Double,
    @Json(name = "take_profit_pct") val takeProfitPct: Double,
    @Json(name = "account_balance") val accountBalance: Double,
    @Json(name = "risk_per_trade") val riskPerTrade: Double,
    val confidence: Double
)

@JsonClass(generateAdapter = true)
data class ExecuteTradeResponseDto(
    val accepted: Boolean,
    val reason: String? = null,
    @Json(name = "position_size") val positionSize: Double = 0.0,
    @Json(name = "max_loss_amount") val maxLossAmount: Double = 0.0,
    @Json(name = "risk_level") val riskLevel: String = "HIGH",
    @Json(name = "expected_value") val expectedValue: Double = 0.0,
    @Json(name = "risk_reward_ratio") val riskRewardRatio: Double = 0.0,
    @Json(name = "target_pct") val targetPct: Double = 0.0,
    @Json(name = "position_notional") val positionNotional: Double = 0.0,
    @Json(name = "governor_decision") val governorDecision: String? = null,
    @Json(name = "governor_reason") val governorReason: String? = null
)

@JsonClass(generateAdapter = true)
data class BrokerStatusItemDto(
    val connected: Boolean = false,
    val accounts: List<String> = emptyList(),
    val label: String = "",
    val configured: Boolean = false,
    val planned: Boolean = false
)

@JsonClass(generateAdapter = true)
data class BacktestRequestDto(
    val symbol: String,
    val timeframe: String,
    @Json(name = "start_date") val startDate: String,
    @Json(name = "end_date") val endDate: String,
    @Json(name = "initial_capital") val initialCapital: Double,
    @Json(name = "risk_per_trade") val riskPerTrade: Double,
    @Json(name = "take_profit_pct") val takeProfitPct: Double,
    @Json(name = "stop_loss_pct") val stopLossPct: Double,
    @Json(name = "max_hold_periods") val maxHoldPeriods: Int,
    @Json(name = "enable_evolution") val enableEvolution: Boolean,
    @Json(name = "enable_compounding") val enableCompounding: Boolean
)

@JsonClass(generateAdapter = true)
data class EquityPointDto(
    val timestamp: String,
    val equity: Double
)

@JsonClass(generateAdapter = true)
data class SimulatedTradeDto(
    val strategy: String,
    val side: String,
    @Json(name = "entry_price") val entryPrice: Double,
    @Json(name = "exit_price") val exitPrice: Double,
    val pnl: Double,
    val outcome: String,
    @Json(name = "entry_time") val entryTime: String,
    @Json(name = "exit_time") val exitTime: String
)

@JsonClass(generateAdapter = true)
data class BacktestResponseDto(
    val symbol: String,
    val timeframe: String,
    @Json(name = "starting_capital") val startingCapital: Double,
    @Json(name = "ending_balance") val endingBalance: Double,
    @Json(name = "total_trades") val totalTrades: Int,
    @Json(name = "win_rate") val winRate: Double,
    @Json(name = "total_pnl") val totalPnl: Double,
    @Json(name = "max_drawdown") val maxDrawdown: Double,
    @Json(name = "sharpe_ratio") val sharpeRatio: Double,
    @Json(name = "stability_score") val stabilityScore: Double = 0.0,
    @Json(name = "equity_curve") val equityCurve: List<EquityPointDto>,
    @Json(name = "trade_history") val tradeHistory: List<SimulatedTradeDto>
)

// Trade Guardrails DTOs

@JsonClass(generateAdapter = true)
data class RiskScoreDto(
    @Json(name = "overall_score") val overallScore: Double,
    @Json(name = "confidence_level") val confidenceLevel: Int,
    @Json(name = "risk_factors") val riskFactors: List<RiskFactorDto> = emptyList(),
    val recommendation: String
)

@JsonClass(generateAdapter = true)
data class RiskFactorDto(
    val name: String,
    val severity: String,
    val impact: Double,
    val description: String
)

@JsonClass(generateAdapter = true)
data class GuardrailStatusDto(
    val passed: Boolean,
    val blockers: List<String> = emptyList(),
    val warnings: List<String> = emptyList(),
    @Json(name = "requires_approval") val requiresApproval: Boolean = false
)

@JsonClass(generateAdapter = true)
data class PortfolioImpactDto(
    @Json(name = "current_exposure") val currentExposure: Double,
    @Json(name = "proposed_exposure") val proposedExposure: Double,
    @Json(name = "exposure_limit") val exposureLimit: Double,
    @Json(name = "drawdown_risk") val drawdownRisk: Double,
    @Json(name = "volatility_impact") val volatilityImpact: String,
    @Json(name = "correlation_concern") val correlationConcern: Boolean,
    @Json(name = "liquidity_risk") val liquidityRisk: String
)

@JsonClass(generateAdapter = true)
data class TradeGuardrailRequestDto(
    val symbol: String,
    val quantity: Double,
    val side: String,
    val price: Double
)

@JsonClass(generateAdapter = true)
data class TradeGuardrailResponseDto(
    @Json(name = "trade_id") val tradeId: String,
    val symbol: String,
    val quantity: Double,
    val side: String,
    val price: Double,
    @Json(name = "risk_score") val riskScore: RiskScoreDto,
    @Json(name = "guardrail_status") val guardrailStatus: GuardrailStatusDto,
    val warnings: List<GuardrailWarningDto> = emptyList(),
    @Json(name = "estimated_impact") val estimatedImpact: PortfolioImpactDto,
    val timestamp: Long = System.currentTimeMillis()
)

@JsonClass(generateAdapter = true)
data class GuardrailWarningDto(
    val id: String,
    val title: String,
    val message: String,
    val severity: String,
    val isDismissible: Boolean = false,
    val actionRequired: Boolean = false
)

@JsonClass(generateAdapter = true)
data class GuardrailApprovalDto(
    @Json(name = "trade_id") val tradeId: String,
    val approved: Boolean,
    val reason: String,
    @Json(name = "user_override") val userOverride: Boolean = false
)

@JsonClass(generateAdapter = true)
data class TradeExecutionAuditDto(
    @Json(name = "trade_id") val tradeId: String,
    val symbol: String,
    val side: String,
    val quantity: Double,
    val price: Double,
    @Json(name = "executed_price") val executedPrice: Double? = null,
    @Json(name = "risk_score_at_execution") val riskScoreAtExecution: RiskScoreDto,
    @Json(name = "guardrail_approval") val guardrailApproval: GuardrailApprovalDto,
    val signals: List<String>,
    @Json(name = "agent_contributions") val agentContributions: List<AgentContributionDto> = emptyList(),
    @Json(name = "execution_status") val executionStatus: String,
    val pnl: Double? = null,
    @Json(name = "created_at") val createdAt: Long = System.currentTimeMillis(),
    @Json(name = "executed_at") val executedAt: Long? = null
)

@JsonClass(generateAdapter = true)
data class AgentContributionDto(
    @Json(name = "agent_id") val agentId: String,
    @Json(name = "agent_name") val agentName: String,
    val confidence: Double,
    val signal: String,
    val reasoning: String
)

// Copilot AI Command Layer DTOs

@JsonClass(generateAdapter = true)
data class CopilotMessageItemDto(
    val role: String,
    val text: String,
    val timestamp: String
)

@JsonClass(generateAdapter = true)
data class CopilotContextResponseDto(
    val greeting: String,
    @Json(name = "first_name") val firstName: String,
    val state: Map<String, Any?> = emptyMap(),
    val history: List<CopilotMessageItemDto> = emptyList(),
    @Json(name = "copilot_mode") val copilotMode: String = "rule-based"
)

@JsonClass(generateAdapter = true)
data class CopilotChatRequestDto(
    val message: String,
    val confirm: Boolean = false,
    @Json(name = "pending_action") val pendingAction: Map<String, Any?>? = null
)

@JsonClass(generateAdapter = true)
data class CopilotChatResponseDto(
    val reply: String,
    val state: Map<String, Any?> = emptyMap(),
    @Json(name = "actions_applied") val actionsApplied: List<String> = emptyList(),
    @Json(name = "requires_confirmation") val requiresConfirmation: Boolean = false,
    @Json(name = "confirmation_prompt") val confirmationPrompt: String? = null,
    @Json(name = "pending_action") val pendingAction: Map<String, Any?>? = null,
    @Json(name = "copilot_mode") val copilotMode: String = "rule-based",
    @Json(name = "parser_used") val parserUsed: String = "rule"
)

@JsonClass(generateAdapter = true)
data class CopilotTelemetrySummaryResponseDto(
    @Json(name = "window_days") val windowDays: Int,
    @Json(name = "total_events") val totalEvents: Int,
    @Json(name = "mode_breakdown") val modeBreakdown: Map<String, Int> = emptyMap(),
    @Json(name = "parser_breakdown") val parserBreakdown: Map<String, Int> = emptyMap(),
    @Json(name = "action_breakdown") val actionBreakdown: Map<String, Int> = emptyMap(),
    @Json(name = "success_rate") val successRate: Double,
    @Json(name = "confirmation_rate") val confirmationRate: Double
)

// Performance Intelligence DTOs

@JsonClass(generateAdapter = true)
data class StrategyStatDto(
    val strategy: String,
    val trades: Int,
    @Json(name = "win_rate") val winRate: Double,
    @Json(name = "net_pnl") val netPnl: Double
)

@JsonClass(generateAdapter = true)
data class TruthDashboardResponseDto(
    @Json(name = "window_days") val windowDays: Int,
    @Json(name = "as_of") val asOf: String,
    val trades: Int,
    @Json(name = "settled_trades") val settledTrades: Int,
    @Json(name = "win_rate") val winRate: Double,
    @Json(name = "net_pnl") val netPnl: Double,
    @Json(name = "best_strategy") val bestStrategy: StrategyStatDto? = null,
    @Json(name = "worst_strategy") val worstStrategy: StrategyStatDto? = null,
    @Json(name = "strategy_breakdown") val strategyBreakdown: List<StrategyStatDto> = emptyList()
)

@JsonClass(generateAdapter = true)
data class AgentWeightEntryDto(
    @Json(name = "agent_name") val agentName: String,
    val weight: Double,
    @Json(name = "raw_score") val rawScore: Double
)

@JsonClass(generateAdapter = true)
data class AgentWeightsResponseDto(
    @Json(name = "regime_weights") val regimeWeights: Map<String, List<AgentWeightEntryDto>> = emptyMap()
)

@JsonClass(generateAdapter = true)
data class ExecutionHistoryEntryDto(
    @Json(name = "execution_id") val executionId: String,
    @Json(name = "cycle_id") val cycleId: String,
    val symbol: String,
    val regime: String,
    val action: String,
    val strategy: String,
    val confidence: Double,
    @Json(name = "risk_level") val riskLevel: String,
    @Json(name = "allocation_pct") val allocationPct: Double,
    val qty: Double,
    val notional: Double,
    val mode: String,
    val submitted: Boolean,
    @Json(name = "order_id") val orderId: String? = null,
    val reason: String? = null,
    val error: String? = null,
    val timestamp: String,
    @Json(name = "outcome_label") val outcomeLabel: String? = null,
    val pnl: Double? = null
)

@JsonClass(generateAdapter = true)
data class ExecutionHistoryResponseDto(
    val executions: List<ExecutionHistoryEntryDto> = emptyList()
)

@JsonClass(generateAdapter = true)
data class AgentPerformanceRowDto(
    @Json(name = "agent_name") val agentName: String,
    val accuracy: Double,
    @Json(name = "win_rate") val winRate: Double,
    @Json(name = "avg_return") val avgReturn: Double,
    @Json(name = "confidence_calibration") val confidenceCalibration: Double,
    @Json(name = "composite_score") val compositeScore: Double
)

@JsonClass(generateAdapter = true)
data class StrategyPerformanceRowDto(
    val strategy: String,
    val trades: Int,
    @Json(name = "win_rate") val winRate: Double,
    @Json(name = "avg_pnl") val avgPnl: Double
)

@JsonClass(generateAdapter = true)
data class PerformanceResponseDto(
    val symbol: String,
    @Json(name = "best_agent") val bestAgent: String,
    @Json(name = "agent_leaderboard") val agentLeaderboard: List<AgentPerformanceRowDto> = emptyList(),
    @Json(name = "top_strategies") val topStrategies: List<StrategyPerformanceRowDto> = emptyList(),
    @Json(name = "by_regime") val byRegime: Map<String, Map<String, Double>> = emptyMap(),
    @Json(name = "generated_at") val generatedAt: String
)