package com.ghost.alpha.data.repository

import com.ghost.alpha.data.remote.CopilotChatRequestDto
import com.ghost.alpha.data.remote.GhostAlphaApiService
import com.ghost.alpha.domain.model.CopilotChatResult
import com.ghost.alpha.domain.model.CopilotContext
import com.ghost.alpha.domain.model.CopilotMessage
import com.ghost.alpha.domain.model.CopilotTelemetrySummary
import com.ghost.alpha.domain.repository.CopilotRepository
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class CopilotRepositoryImpl @Inject constructor(
    private val apiService: GhostAlphaApiService
) : CopilotRepository {

    override suspend fun getContext(): CopilotContext {
        val dto = apiService.getCopilotContext()
        return CopilotContext(
            greeting = dto.greeting,
            firstName = dto.firstName,
            state = dto.state.mapValues { (_, v) -> v?.toString().orEmpty() },
            history = dto.history.map {
                CopilotMessage(
                    role = it.role,
                    text = it.text,
                    timestamp = runCatching { Instant.parse(it.timestamp) }.getOrDefault(Instant.now())
                )
            },
            mode = dto.copilotMode
        )
    }

    override suspend fun sendMessage(
        message: String,
        confirm: Boolean,
        pendingAction: Map<String, String>?
    ): CopilotChatResult {
        val dto = apiService.sendCopilotMessage(
            CopilotChatRequestDto(
                message = message,
                confirm = confirm,
                pendingAction = pendingAction
            )
        )
        return CopilotChatResult(
            reply = dto.reply,
            state = dto.state.mapValues { (_, v) -> v?.toString().orEmpty() },
            actionsApplied = dto.actionsApplied,
            requiresConfirmation = dto.requiresConfirmation,
            confirmationPrompt = dto.confirmationPrompt,
            pendingAction = dto.pendingAction?.mapValues { (_, v) -> v?.toString().orEmpty() },
            mode = dto.copilotMode,
            parserUsed = dto.parserUsed
        )
    }

    override suspend fun getTelemetrySummary(): CopilotTelemetrySummary {
        val dto = apiService.getCopilotTelemetrySummary()
        return CopilotTelemetrySummary(
            windowDays = dto.windowDays,
            totalEvents = dto.totalEvents,
            modeBreakdown = dto.modeBreakdown,
            parserBreakdown = dto.parserBreakdown,
            actionBreakdown = dto.actionBreakdown,
            successRate = dto.successRate,
            confirmationRate = dto.confirmationRate
        )
    }
}
