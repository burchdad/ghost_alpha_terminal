package com.ghost.alpha.data.repository

import com.ghost.alpha.data.local.GhostAlphaDatabase
import com.ghost.alpha.data.remote.GhostAlphaApiService
import com.ghost.alpha.data.remote.GuardrailApprovalDto
import com.ghost.alpha.data.remote.TradeGuardrailRequestDto
import com.ghost.alpha.domain.model.GuardrailDecision
import com.ghost.alpha.domain.model.RiskFactor
import com.ghost.alpha.domain.model.RiskScore
import com.ghost.alpha.domain.model.RiskSeverity
import com.ghost.alpha.domain.model.TradeExecutionAudit
import com.ghost.alpha.domain.model.TradeGuardrail
import com.ghost.alpha.domain.repository.GuardrailRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import javax.inject.Inject

class GuardrailRepositoryImpl @Inject constructor(
    private val apiService: GhostAlphaApiService,
    private val database: GhostAlphaDatabase
) : GuardrailRepository {

    private val tradeDecisionsFlow = MutableSharedFlow<GuardrailDecision>(replay = 0)

    override suspend fun assessTradeRisks(
        symbol: String,
        quantity: Double,
        side: String,
        price: Double
    ): Result<TradeGuardrail> = try {
        val request = TradeGuardrailRequestDto(
            symbol = symbol,
            quantity = quantity,
            side = side,
            price = price
        )
        val response = apiService.assessTradeRisks(request)
        val guardrail = mapGuardrailResponseToModel(response)
        Result.success(guardrail)
    } catch (e: Exception) {
        Result.failure(e)
    }

    override suspend fun approveTradeWithGuardrails(
        tradeId: String,
        approved: Boolean,
        reason: String,
        userOverride: Boolean
    ): Result<TradeExecutionAudit> = try {
        val request = GuardrailApprovalDto(
            tradeId = tradeId,
            approved = approved,
            reason = reason,
            userOverride = userOverride
        )
        val response = apiService.approveTradeWithGuardrails(request)
        val audit = mapAuditResponseToModel(response)
        Result.success(audit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    override suspend fun getTradeAudit(tradeId: String): Result<TradeExecutionAudit> = try {
        val response = apiService.getTradeAudit(tradeId)
        val audit = mapAuditResponseToModel(response)
        Result.success(audit)
    } catch (e: Exception) {
        Result.failure(e)
    }

    override suspend fun getRecentTradeAudits(limit: Int): Result<List<TradeExecutionAudit>> = try {
        val responses = apiService.getRecentTradeAudits(limit)
        val audits = responses.map { mapAuditResponseToModel(it) }
        Result.success(audits)
    } catch (e: Exception) {
        Result.failure(e)
    }

    override fun observeTradeDecisions(): Flow<GuardrailDecision> = tradeDecisionsFlow

    internal suspend fun emitTradeDecision(decision: GuardrailDecision) {
        tradeDecisionsFlow.emit(decision)
    }

    private fun mapGuardrailResponseToModel(dto: com.ghost.alpha.data.remote.TradeGuardrailResponseDto) =
        TradeGuardrail(
            tradeId = dto.tradeId,
            symbol = dto.symbol,
            quantity = dto.quantity,
            side = dto.side,
            price = dto.price,
            riskScore = RiskScore(
                overallScore = dto.riskScore.overallScore,
                confidenceLevel = dto.riskScore.confidenceLevel,
                riskFactors = dto.riskScore.riskFactors.map {
                    RiskFactor(
                        name = it.name,
                        severity = parseSeverity(it.severity),
                        impact = it.impact,
                        description = it.description
                    )
                },
                recommendation = dto.riskScore.recommendation
            ),
            guardrailStatus = com.ghost.alpha.domain.model.GuardrailStatus(
                passed = dto.guardrailStatus.passed,
                blockers = dto.guardrailStatus.blockers,
                warnings = dto.guardrailStatus.warnings,
                requiresApproval = dto.guardrailStatus.requiresApproval
            ),
            warnings = dto.warnings.map {
                com.ghost.alpha.domain.model.GuardrailWarning(
                    id = it.id,
                    title = it.title,
                    message = it.message,
                    severity = parseSeverity(it.severity),
                    isDismissible = it.isDismissible,
                    actionRequired = it.actionRequired
                )
            },
            estimatedImpact = com.ghost.alpha.domain.model.PortfolioImpact(
                currentExposure = dto.estimatedImpact.currentExposure,
                proposedExposure = dto.estimatedImpact.proposedExposure,
                exposureLimit = dto.estimatedImpact.exposureLimit,
                drawdownRisk = dto.estimatedImpact.drawdownRisk,
                volatilityImpact = dto.estimatedImpact.volatilityImpact,
                correlationConcern = dto.estimatedImpact.correlationConcern,
                liquidityRisk = dto.estimatedImpact.liquidityRisk
            ),
            timestamp = dto.timestamp
        )

    private fun mapAuditResponseToModel(dto: com.ghost.alpha.data.remote.TradeExecutionAuditDto) =
        TradeExecutionAudit(
            tradeId = dto.tradeId,
            symbol = dto.symbol,
            side = dto.side,
            quantity = dto.quantity,
            price = dto.price,
            executedPrice = dto.executedPrice,
            riskScoreAtExecution = RiskScore(
                overallScore = dto.riskScoreAtExecution.overallScore,
                confidenceLevel = dto.riskScoreAtExecution.confidenceLevel,
                riskFactors = dto.riskScoreAtExecution.riskFactors.map {
                    RiskFactor(
                        name = it.name,
                        severity = parseSeverity(it.severity),
                        impact = it.impact,
                        description = it.description
                    )
                },
                recommendation = dto.riskScoreAtExecution.recommendation
            ),
            guardrailApproval = com.ghost.alpha.domain.model.GuardrailDecision(
                tradeId = dto.guardrailApproval.tradeId,
                approved = dto.guardrailApproval.approved,
                reason = dto.guardrailApproval.reason,
                userOverride = dto.guardrailApproval.userOverride,
                timestamp = System.currentTimeMillis()
            ),
            signals = dto.signals,
            agentContributions = dto.agentContributions.map {
                com.ghost.alpha.domain.model.AgentContribution(
                    agentId = it.agentId,
                    agentName = it.agentName,
                    confidence = it.confidence,
                    signal = it.signal,
                    reasoning = it.reasoning
                )
            },
            executionStatus = com.ghost.alpha.domain.model.ExecutionStatus.valueOf(
                dto.executionStatus.uppercase().replace("-", "_")
            ),
            pnl = dto.pnl,
            createdAt = dto.createdAt,
            executedAt = dto.executedAt
        )

    private fun parseSeverity(severity: String): RiskSeverity = when (severity.uppercase()) {
        "LOW" -> RiskSeverity.LOW
        "MEDIUM" -> RiskSeverity.MEDIUM
        "HIGH" -> RiskSeverity.HIGH
        "CRITICAL" -> RiskSeverity.CRITICAL
        else -> RiskSeverity.MEDIUM
    }
}
