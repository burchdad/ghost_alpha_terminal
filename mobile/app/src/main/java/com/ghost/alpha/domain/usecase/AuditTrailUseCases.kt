package com.ghost.alpha.domain.usecase

import com.ghost.alpha.domain.repository.AuditTrailRepository
import javax.inject.Inject

class ListDecisionAuditsUseCase @Inject constructor(
    private val repository: AuditTrailRepository
) {
    suspend operator fun invoke(limit: Int = 50, symbol: String? = null, status: String? = null) =
        repository.listDecisionAudits(limit = limit, symbol = symbol, status = status)
}

class GetDecisionReplayUseCase @Inject constructor(
    private val repository: AuditTrailRepository
) {
    suspend operator fun invoke(auditId: String) = repository.getDecisionReplay(auditId)
}

class GetDecisionAuditDetailUseCase @Inject constructor(
    private val repository: AuditTrailRepository
) {
    suspend operator fun invoke(auditId: String) = repository.getDecisionAuditDetail(auditId)
}
