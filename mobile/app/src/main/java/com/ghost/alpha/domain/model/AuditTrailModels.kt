package com.ghost.alpha.domain.model

import java.time.Instant

data class DecisionAuditSummary(
    val auditId: String,
    val timestamp: Instant,
    val decisionType: String,
    val symbol: String,
    val status: String,
    val cycleId: String?
)

data class DecisionReplayStep(
    val stage: String,
    val title: String,
    val summary: String,
    val payload: Map<String, String>
)

data class DecisionReplay(
    val auditId: String,
    val symbol: String,
    val decisionType: String,
    val status: String,
    val generatedAt: Instant,
    val replaySteps: List<DecisionReplayStep>,
    val whyNot: List<String>
)

data class DecisionAuditDetail(
    val auditId: String,
    val timestamp: Instant,
    val decisionType: String,
    val symbol: String,
    val status: String,
    val cycleId: String?,
    val governorSnapshot: Map<String, String>,
    val allocationSnapshot: Map<String, String>,
    val executionSnapshot: Map<String, String>,
    val contextSnapshot: Map<String, String>,
    val explainabilitySnapshot: Map<String, String>
)
