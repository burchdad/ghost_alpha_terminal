package com.ghost.alpha.domain.model

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

/**
 * Trade Guardrails: Risk assessment and safety gates before execution
 */

@Serializable
data class TradeGuardrail(
    val tradeId: String,
    val symbol: String,
    val quantity: Double,
    val side: String,  // BUY or SELL
    val price: Double,
    val riskScore: RiskScore,
    val guardrailStatus: GuardrailStatus,
    val warnings: List<GuardrailWarning> = emptyList(),
    val estimatedImpact: PortfolioImpact,
    val timestamp: Long = System.currentTimeMillis()
)

@Serializable
data class RiskScore(
    val overallScore: Double,  // 0-100, higher = riskier
    val confidenceLevel: Int,  // 0-100
    val riskFactors: List<RiskFactor> = emptyList(),
    val recommendation: String  // "PROCEED", "CAUTIOUS", "BLOCK"
)

@Serializable
data class RiskFactor(
    val name: String,  // e.g., "High Volatility", "Low Confidence", "Concentrated Position"
    val severity: RiskSeverity,
    val impact: Double,  // 0-1, contribution to overall score
    val description: String
)

@Serializable
enum class RiskSeverity {
    @SerialName("low")
    LOW,
    @SerialName("medium")
    MEDIUM,
    @SerialName("high")
    HIGH,
    @SerialName("critical")
    CRITICAL
}

@Serializable
data class GuardrailStatus(
    val passed: Boolean,
    val blockers: List<String> = emptyList(),  // Hard blocks
    val warnings: List<String> = emptyList(),  // Warnings but passable
    val requiresApproval: Boolean = false
)

@Serializable
data class GuardrailWarning(
    val id: String,
    val title: String,
    val message: String,
    val severity: RiskSeverity,
    val isDismissible: Boolean = false,
    val actionRequired: Boolean = false
)

@Serializable
data class PortfolioImpact(
    val currentExposure: Double,  // % of portfolio
    val proposedExposure: Double,  // % after trade
    val exposureLimit: Double,  // max allowed %
    val drawdownRisk: Double,  // estimated max loss %
    val volatilityImpact: String,  // "Low", "Medium", "High"
    val correlationConcern: Boolean,  // true if highly correlated with existing positions
    val liquidityRisk: String  // "Low", "Medium", "High"
)

@Serializable
data class GuardrailDecision(
    val tradeId: String,
    val approved: Boolean,
    val reason: String,
    val userOverride: Boolean = false,
    val timestamp: Long = System.currentTimeMillis()
)

@Serializable
data class TradeExecutionAudit(
    val tradeId: String,
    val symbol: String,
    val side: String,
    val quantity: Double,
    val price: Double,
    val executedPrice: Double? = null,
    val riskScoreAtExecution: RiskScore,
    val guardrailApproval: GuardrailDecision,
    val signals: List<String>,  // Signal IDs that triggered the trade
    val agentContributions: List<AgentContribution> = emptyList(),
    val executionStatus: ExecutionStatus,
    val pnl: Double? = null,
    val createdAt: Long = System.currentTimeMillis(),
    val executedAt: Long? = null
)

@Serializable
enum class ExecutionStatus {
    @SerialName("pending_guardrails")
    PENDING_GUARDRAILS,
    @SerialName("pending_approval")
    PENDING_APPROVAL,
    @SerialName("approved")
    APPROVED,
    @SerialName("rejected")
    REJECTED,
    @SerialName("executing")
    EXECUTING,
    @SerialName("executed")
    EXECUTED,
    @SerialName("failed")
    FAILED,
    @SerialName("cancelled")
    CANCELLED
}

@Serializable
data class AgentContribution(
    val agentId: String,
    val agentName: String,
    val confidence: Double,  // 0-1
    val signal: String,  // BUY, SELL, HOLD
    val reasoning: String
)
