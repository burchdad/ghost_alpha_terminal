package com.ghost.alpha.domain.repository

import com.ghost.alpha.domain.model.AutonomousConfig
import com.ghost.alpha.domain.model.AutonomousStatus
import com.ghost.alpha.domain.model.AutonomyControlSnapshot
import com.ghost.alpha.domain.model.ControlStatus
import com.ghost.alpha.domain.model.RiskLimits

interface AutonomyRepository {
    suspend fun getControlStatus(): ControlStatus
    suspend fun getAutonomousStatus(): AutonomousStatus
    suspend fun updateAutonomousMode(config: AutonomousConfig): AutonomousStatus
    suspend fun runAutonomousOnce(): AutonomousStatus
    suspend fun setTradingEnabled(enabled: Boolean): Boolean
    suspend fun updateRiskLimits(dailyLossLimitPct: Double, maxDrawdownLimitPct: Double): RiskLimits
    suspend fun getAutonomySnapshot(symbolFilter: String? = null): AutonomyControlSnapshot
}
