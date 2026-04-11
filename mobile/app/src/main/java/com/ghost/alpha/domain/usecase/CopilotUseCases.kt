package com.ghost.alpha.domain.usecase

import com.ghost.alpha.domain.repository.CopilotRepository
import javax.inject.Inject

class GetCopilotContextUseCase @Inject constructor(
    private val repository: CopilotRepository
) {
    suspend operator fun invoke() = repository.getContext()
}

class SendCopilotMessageUseCase @Inject constructor(
    private val repository: CopilotRepository
) {
    suspend operator fun invoke(
        message: String,
        confirm: Boolean = false,
        pendingAction: Map<String, String>? = null
    ) = repository.sendMessage(message, confirm, pendingAction)
}

class GetCopilotTelemetrySummaryUseCase @Inject constructor(
    private val repository: CopilotRepository
) {
    suspend operator fun invoke() = repository.getTelemetrySummary()
}
