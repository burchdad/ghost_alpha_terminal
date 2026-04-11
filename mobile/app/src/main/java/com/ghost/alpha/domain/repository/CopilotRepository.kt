package com.ghost.alpha.domain.repository

import com.ghost.alpha.domain.model.CopilotChatResult
import com.ghost.alpha.domain.model.CopilotContext
import com.ghost.alpha.domain.model.CopilotTelemetrySummary

interface CopilotRepository {
    suspend fun getContext(): CopilotContext
    suspend fun sendMessage(
        message: String,
        confirm: Boolean = false,
        pendingAction: Map<String, String>? = null
    ): CopilotChatResult
    suspend fun getTelemetrySummary(): CopilotTelemetrySummary
}
