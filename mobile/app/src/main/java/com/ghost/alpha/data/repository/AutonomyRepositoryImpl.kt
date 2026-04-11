package com.ghost.alpha.data.repository

import com.ghost.alpha.data.remote.AutonomousModeUpdateRequestDto
import com.ghost.alpha.data.remote.GhostAlphaApiService
import com.ghost.alpha.data.remote.KillSwitchUpdateRequestDto
import com.ghost.alpha.data.remote.RiskLimitUpdateRequestDto
import com.ghost.alpha.domain.model.AutonomousConfig
import com.ghost.alpha.domain.model.AutonomousFeedItem
import com.ghost.alpha.domain.model.AutonomousStatus
import com.ghost.alpha.domain.model.AutonomyControlSnapshot
import com.ghost.alpha.domain.model.ComplianceMode
import com.ghost.alpha.domain.model.ControlStatus
import com.ghost.alpha.domain.model.RejectedTradeLog
import com.ghost.alpha.domain.model.RiskLimits
import com.ghost.alpha.domain.repository.AutonomyRepository
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

@Singleton
class AutonomyRepositoryImpl @Inject constructor(
    private val apiService: GhostAlphaApiService
) : AutonomyRepository {

    override suspend fun getControlStatus(): ControlStatus {
        val dto = apiService.getControlStatus()
        return dto.toDomain()
    }

    override suspend fun getAutonomousStatus(): AutonomousStatus {
        val dto = apiService.getAutonomousStatus()
        return AutonomousStatus(
            enabled = dto.enabled,
            intervalSeconds = dto.intervalSeconds,
            symbols = dto.symbols,
            cyclesRun = dto.cyclesRun,
            lastRunAt = dto.lastRunAt?.let(::parseInstant),
            lastError = dto.lastError
        )
    }

    override suspend fun updateAutonomousMode(config: AutonomousConfig): AutonomousStatus {
        val dto = apiService.updateAutonomousMode(
            AutonomousModeUpdateRequestDto(
                enabled = config.enabled,
                intervalSeconds = config.intervalSeconds,
                symbols = config.symbols
            )
        )
        return AutonomousStatus(
            enabled = dto.enabled,
            intervalSeconds = dto.intervalSeconds,
            symbols = dto.symbols,
            cyclesRun = dto.cyclesRun,
            lastRunAt = dto.lastRunAt?.let(::parseInstant),
            lastError = dto.lastError
        )
    }

    override suspend fun runAutonomousOnce(): AutonomousStatus {
        val dto = apiService.runAutonomousOnce()
        return AutonomousStatus(
            enabled = dto.enabled,
            intervalSeconds = dto.intervalSeconds,
            symbols = dto.symbols,
            cyclesRun = dto.cyclesRun,
            lastRunAt = dto.lastRunAt?.let(::parseInstant),
            lastError = dto.lastError
        )
    }

    override suspend fun setTradingEnabled(enabled: Boolean): Boolean {
        val response = apiService.updateKillSwitch(KillSwitchUpdateRequestDto(tradingEnabled = enabled))
        return response.tradingEnabled
    }

    override suspend fun updateRiskLimits(dailyLossLimitPct: Double, maxDrawdownLimitPct: Double): RiskLimits {
        val dto = apiService.updateRiskLimits(
            RiskLimitUpdateRequestDto(
                dailyLossLimitPct = dailyLossLimitPct,
                maxDrawdownLimitPct = maxDrawdownLimitPct
            )
        )
        return RiskLimits(
            dailyLossLimitPct = dto.dailyLossLimitPct,
            maxDrawdownLimitPct = dto.maxDrawdownLimitPct,
            dailyLossLimit = dto.dailyLossLimit
        )
    }

    override suspend fun getAutonomySnapshot(symbolFilter: String?): AutonomyControlSnapshot {
        val control = apiService.getControlStatus()
        val execution = apiService.getExecutionHistory(limit = 60)
        val audits = apiService.getDecisionAudits(limit = 60, symbol = symbolFilter?.takeIf { it.isNotBlank() })

        val controlDomain = control.toDomain()
        val feed = execution.executions.map {
            val reason = it.reason?.takeIf { msg -> msg.isNotBlank() }
                ?: audits.entries.firstOrNull { audit -> audit.cycleId == it.cycleId }?.status
                ?: "Submitted by autonomous orchestration"
            AutonomousFeedItem(
                id = it.executionId,
                timestamp = parseInstant(it.timestamp),
                symbol = it.symbol,
                strategy = it.strategy,
                status = if (it.submitted) (it.outcomeLabel ?: "SUBMITTED") else "REJECTED",
                confidence = it.confidence,
                pnl = it.pnl,
                why = reason
            )
        }

        val manualOnly = !controlDomain.tradingEnabled || !controlDomain.autonomous.enabled
        val strictGuardrails = controlDomain.dailyLossLimitPct <= 0.03 && controlDomain.maxDrawdownLimitPct <= 0.08

        val exportMap = mapOf(
            "generated_at" to Instant.now().toString(),
            "control" to mapOf(
                "trading_enabled" to controlDomain.tradingEnabled,
                "autonomous_enabled" to controlDomain.autonomous.enabled,
                "daily_loss_limit_pct" to controlDomain.dailyLossLimitPct,
                "max_drawdown_limit_pct" to controlDomain.maxDrawdownLimitPct
            ),
            "recent_feed" to feed.take(25).map {
                mapOf(
                    "id" to it.id,
                    "timestamp" to it.timestamp.toString(),
                    "symbol" to it.symbol,
                    "strategy" to it.strategy,
                    "status" to it.status,
                    "confidence" to it.confidence,
                    "pnl" to it.pnl,
                    "why" to it.why
                )
            }
        )

        return AutonomyControlSnapshot(
            controlStatus = controlDomain,
            feed = feed,
            complianceMode = ComplianceMode(manualOnly = manualOnly, strictGuardrails = strictGuardrails),
            auditExportJson = Json { prettyPrint = true }.encodeToString(exportMap)
        )
    }

    private fun parseInstant(value: String): Instant = runCatching { Instant.parse(value) }.getOrDefault(Instant.now())

    private fun com.ghost.alpha.data.remote.ControlStatusResponseDto.toDomain(): ControlStatus {
        return ControlStatus(
            tradingEnabled = tradingEnabled,
            systemStatus = systemStatus,
            mode = mode,
            dailyPnl = dailyPnl,
            dailyLoss = dailyLoss,
            dailyLossLimit = dailyLossLimit,
            dailyLossLimitPct = dailyLossLimitPct,
            rollingDrawdown = rollingDrawdown,
            rollingDrawdownPct = rollingDrawdownPct,
            maxDrawdownLimitPct = maxDrawdownLimitPct,
            autonomous = AutonomousStatus(
                enabled = autonomousEnabled,
                intervalSeconds = autonomousIntervalSeconds,
                symbols = autonomousSymbols,
                cyclesRun = autonomousCyclesRun,
                lastRunAt = autonomousLastRunAt?.let(::parseInstant),
                lastError = autonomousLastError
            ),
            rejectedTrades = rejectedTrades.map {
                RejectedTradeLog(
                    timestamp = parseInstant(it.timestamp),
                    symbol = it.symbol,
                    reason = it.reason
                )
            }
        )
    }
}
