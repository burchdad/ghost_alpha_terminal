package com.ghost.alpha.domain.repository

import com.ghost.alpha.domain.model.DecisionAuditDetail
import com.ghost.alpha.domain.model.DecisionAuditSummary
import com.ghost.alpha.domain.model.DecisionReplay

interface AuditTrailRepository {
    suspend fun listDecisionAudits(
        limit: Int = 50,
        symbol: String? = null,
        status: String? = null
    ): List<DecisionAuditSummary>

    suspend fun getDecisionReplay(auditId: String): DecisionReplay

    suspend fun getDecisionAuditDetail(auditId: String): DecisionAuditDetail
}
