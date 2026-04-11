package com.ghost.alpha.domain.model

import java.time.Instant

data class AutonomousStatus(
    val enabled: Boolean,
    val intervalSeconds: Int,
    val symbols: List<String>,
    val cyclesRun: Int,
    val lastRunAt: Instant?,
    val lastError: String?
)

data class RiskLimits(
    val dailyLossLimitPct: Double,
    val maxDrawdownLimitPct: Double,
    val dailyLossLimit: Double
)

data class ControlStatus(
    val tradingEnabled: Boolean,
    val systemStatus: String,
    val mode: String,
    val dailyPnl: Double,
    val dailyLoss: Double,
    val dailyLossLimit: Double,
    val dailyLossLimitPct: Double,
    val rollingDrawdown: Double,
    val rollingDrawdownPct: Double,
    val maxDrawdownLimitPct: Double,
    val autonomous: AutonomousStatus,
    val rejectedTrades: List<RejectedTradeLog>
)

data class RejectedTradeLog(
    val timestamp: Instant,
    val symbol: String,
    val reason: String
)

data class AutonomousConfig(
    val enabled: Boolean,
    val intervalSeconds: Int,
    val symbols: List<String>
)

data class AutonomousFeedItem(
    val id: String,
    val timestamp: Instant,
    val symbol: String,
    val strategy: String,
    val status: String,
    val confidence: Double,
    val pnl: Double?,
    val why: String
)

data class ComplianceMode(
    val manualOnly: Boolean,
    val strictGuardrails: Boolean
)

data class AutonomyControlSnapshot(
    val controlStatus: ControlStatus,
    val feed: List<AutonomousFeedItem>,
    val complianceMode: ComplianceMode,
    val auditExportJson: String?
)
