package com.ghost.alpha.domain.usecase

import com.ghost.alpha.domain.model.TradeExecutionAudit
import com.ghost.alpha.domain.model.TradeGuardrail
import com.ghost.alpha.domain.repository.GuardrailRepository
import javax.inject.Inject

class AssessTradeRisksUseCase @Inject constructor(
    private val guardrailRepository: GuardrailRepository
) {
    suspend operator fun invoke(
        symbol: String,
        quantity: Double,
        side: String,
        price: Double
    ): Result<TradeGuardrail> = guardrailRepository.assessTradeRisks(symbol, quantity, side, price)
}

class ApproveTradeWithGuardrailsUseCase @Inject constructor(
    private val guardrailRepository: GuardrailRepository
) {
    suspend operator fun invoke(
        tradeId: String,
        approved: Boolean,
        reason: String,
        userOverride: Boolean = false
    ): Result<TradeExecutionAudit> =
        guardrailRepository.approveTradeWithGuardrails(tradeId, approved, reason, userOverride)
}

class GetTradeAuditUseCase @Inject constructor(
    private val guardrailRepository: GuardrailRepository
) {
    suspend operator fun invoke(tradeId: String): Result<TradeExecutionAudit> =
        guardrailRepository.getTradeAudit(tradeId)
}

class GetRecentTradeAuditsUseCase @Inject constructor(
    private val guardrailRepository: GuardrailRepository
) {
    suspend operator fun invoke(limit: Int = 10): Result<List<TradeExecutionAudit>> =
        guardrailRepository.getRecentTradeAudits(limit)
}
