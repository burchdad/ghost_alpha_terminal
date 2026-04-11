package com.ghost.alpha.domain.repository

import com.ghost.alpha.domain.model.BacktestRequest
import com.ghost.alpha.domain.model.BacktestResult
import com.ghost.alpha.domain.model.PortfolioSnapshot
import com.ghost.alpha.domain.model.Position
import com.ghost.alpha.domain.model.Signal
import com.ghost.alpha.domain.model.SwarmSignal
import com.ghost.alpha.domain.model.TradeExecutionRequest
import com.ghost.alpha.domain.model.TradeExecutionResult
import kotlinx.coroutines.flow.Flow

interface MarketRepository {
    fun observeCachedSignals(): Flow<List<Signal>>
    fun observeCachedPositions(): Flow<List<Position>>
    suspend fun fetchSignal(symbol: String): Signal
    suspend fun fetchPortfolio(): PortfolioSnapshot
    suspend fun fetchSwarmSignal(symbol: String): SwarmSignal
    suspend fun executeTrade(request: TradeExecutionRequest): TradeExecutionResult
    suspend fun runBacktest(request: BacktestRequest): BacktestResult
}