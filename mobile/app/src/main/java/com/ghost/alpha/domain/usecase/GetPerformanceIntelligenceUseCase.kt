package com.ghost.alpha.domain.usecase

import com.ghost.alpha.domain.model.PerformanceIntelligenceSnapshot
import com.ghost.alpha.domain.repository.PerformanceRepository
import javax.inject.Inject

class GetPerformanceIntelligenceUseCase @Inject constructor(
    private val repository: PerformanceRepository
) {
    suspend operator fun invoke(days: Int = 7, symbol: String = "AAPL"): PerformanceIntelligenceSnapshot {
        return repository.getPerformanceIntelligence(days = days, symbol = symbol)
    }
}
