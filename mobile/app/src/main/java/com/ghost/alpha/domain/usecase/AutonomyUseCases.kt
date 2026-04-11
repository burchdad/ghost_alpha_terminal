package com.ghost.alpha.domain.usecase

import com.ghost.alpha.domain.model.AutonomousConfig
import com.ghost.alpha.domain.repository.AutonomyRepository
import javax.inject.Inject

class GetAutonomySnapshotUseCase @Inject constructor(
    private val repository: AutonomyRepository
) {
    suspend operator fun invoke(symbolFilter: String? = null) = repository.getAutonomySnapshot(symbolFilter)
}

class UpdateAutonomousModeUseCase @Inject constructor(
    private val repository: AutonomyRepository
) {
    suspend operator fun invoke(config: AutonomousConfig) = repository.updateAutonomousMode(config)
}

class RunAutonomousOnceUseCase @Inject constructor(
    private val repository: AutonomyRepository
) {
    suspend operator fun invoke() = repository.runAutonomousOnce()
}

class ToggleTradingUseCase @Inject constructor(
    private val repository: AutonomyRepository
) {
    suspend operator fun invoke(enabled: Boolean) = repository.setTradingEnabled(enabled)
}

class UpdateAutonomyRiskLimitsUseCase @Inject constructor(
    private val repository: AutonomyRepository
) {
    suspend operator fun invoke(dailyLossLimitPct: Double, maxDrawdownLimitPct: Double) =
        repository.updateRiskLimits(dailyLossLimitPct, maxDrawdownLimitPct)
}
