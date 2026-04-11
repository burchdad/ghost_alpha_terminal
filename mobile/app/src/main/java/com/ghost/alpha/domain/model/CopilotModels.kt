package com.ghost.alpha.domain.model

import java.time.Instant

data class CopilotMessage(
    val role: String,
    val text: String,
    val timestamp: Instant
)

data class CopilotContext(
    val greeting: String,
    val firstName: String,
    val state: Map<String, String>,
    val history: List<CopilotMessage>,
    val mode: String
)

data class CopilotChatResult(
    val reply: String,
    val state: Map<String, String>,
    val actionsApplied: List<String>,
    val requiresConfirmation: Boolean,
    val confirmationPrompt: String?,
    val pendingAction: Map<String, String>?,
    val mode: String,
    val parserUsed: String
)

data class CopilotTelemetrySummary(
    val windowDays: Int,
    val totalEvents: Int,
    val modeBreakdown: Map<String, Int>,
    val parserBreakdown: Map<String, Int>,
    val actionBreakdown: Map<String, Int>,
    val successRate: Double,
    val confirmationRate: Double
)
