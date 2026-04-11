package com.ghost.alpha.domain.repository

import com.ghost.alpha.domain.model.PerformanceIntelligenceSnapshot

interface PerformanceRepository {
    suspend fun getPerformanceIntelligence(days: Int = 7, symbol: String = "AAPL"): PerformanceIntelligenceSnapshot
}
