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