package com.ghost.alpha.domain.repository

import com.ghost.alpha.domain.model.GuardrailDecision
import com.ghost.alpha.domain.model.TradeExecutionAudit
import com.ghost.alpha.domain.model.TradeGuardrail
import kotlinx.coroutines.flow.Flow

interface GuardrailRepository {
    /**
     * Assess trade risks before execution
     */
    suspend fun assessTradeRisks(
        symbol: String,
        quantity: Double,
        side: String,
        price: Double
    ): Result<TradeGuardrail>

    /**
     * Approve or reject a trade based on guardrails
     */
    suspend fun approveTradeWithGuardrails(
        tradeId: String,
        approved: Boolean,
        reason: String,
        userOverride: Boolean = false
    ): Result<TradeExecutionAudit>

    /**
     * Get trade execution audit log
     */
    suspend fun getTradeAudit(tradeId: String): Result<TradeExecutionAudit>

    /**
     * Get recent trade audits
     */
    suspend fun getRecentTradeAudits(limit: Int = 10): Result<List<TradeExecutionAudit>>

    /**
     * Stream trade decisions (for real-time updates)
     */
    fun observeTradeDecisions(): Flow<GuardrailDecision>
}
