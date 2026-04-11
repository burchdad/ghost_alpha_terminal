package com.ghost.alpha.data.repository

import com.ghost.alpha.data.remote.GhostAlphaApiService
import com.ghost.alpha.domain.model.DecisionAuditDetail
import com.ghost.alpha.domain.model.DecisionAuditSummary
import com.ghost.alpha.domain.model.DecisionReplay
import com.ghost.alpha.domain.model.DecisionReplayStep
import com.ghost.alpha.domain.repository.AuditTrailRepository
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuditTrailRepositoryImpl @Inject constructor(
    private val apiService: GhostAlphaApiService
) : AuditTrailRepository {

    override suspend fun listDecisionAudits(limit: Int, symbol: String?, status: String?): List<DecisionAuditSummary> {
        return apiService.getDecisionAudits(limit = limit, symbol = symbol?.takeIf { it.isNotBlank() }, status = status?.takeIf { it.isNotBlank() })
            .entries
            .map {
                DecisionAuditSummary(
                    auditId = it.auditId,
                    timestamp = parseInstant(it.timestamp),
                    decisionType = it.decisionType,
                    symbol = it.symbol,
                    status = it.status,
                    cycleId = it.cycleId
                )
            }
    }

    override suspend fun getDecisionReplay(auditId: String): DecisionReplay {
        val dto = apiService.getDecisionReplay(auditId)
        return DecisionReplay(
            auditId = dto.auditId,
            symbol = dto.symbol,
            decisionType = dto.decisionType,
            status = dto.status,
            generatedAt = parseInstant(dto.generatedAt),
            replaySteps = dto.replaySteps.map {
                DecisionReplayStep(
                    stage = it.stage,
                    title = it.title,
                    summary = it.summary,
                    payload = it.payload.mapValues { (_, value) -> value?.toString().orEmpty() }
                )
            },
            whyNot = dto.whyNot
        )
    }

    override suspend fun getDecisionAuditDetail(auditId: String): DecisionAuditDetail {
        val dto = apiService.getDecisionAuditDetail(auditId)
        return DecisionAuditDetail(
            auditId = dto.auditId,
            timestamp = parseInstant(dto.timestamp),
            decisionType = dto.decisionType,
            symbol = dto.symbol,
            status = dto.status,
            cycleId = dto.cycleId,
            governorSnapshot = dto.governorSnapshot.mapValues { (_, value) -> value?.toString().orEmpty() },
            allocationSnapshot = dto.allocationSnapshot.mapValues { (_, value) -> value?.toString().orEmpty() },
            executionSnapshot = dto.executionSnapshot.mapValues { (_, value) -> value?.toString().orEmpty() },
            contextSnapshot = dto.contextSnapshot.mapValues { (_, value) -> value?.toString().orEmpty() },
            explainabilitySnapshot = dto.explainabilitySnapshot.mapValues { (_, value) -> value?.toString().orEmpty() }
        )
    }

    private fun parseInstant(value: String): Instant = runCatching { Instant.parse(value) }.getOrDefault(Instant.now())
}
