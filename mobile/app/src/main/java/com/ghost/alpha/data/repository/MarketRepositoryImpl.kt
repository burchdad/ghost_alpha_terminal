package com.ghost.alpha.data.repository

import com.ghost.alpha.data.local.PositionDao
import com.ghost.alpha.data.local.SignalDao
import com.ghost.alpha.data.local.TradeHistoryDao
import com.ghost.alpha.data.local.toEntity
import com.ghost.alpha.data.remote.GhostAlphaApiService
import com.ghost.alpha.domain.model.BacktestRequest
import com.ghost.alpha.domain.model.BacktestResult
import com.ghost.alpha.domain.model.PortfolioSnapshot
import com.ghost.alpha.domain.model.Position
import com.ghost.alpha.domain.model.Signal
import com.ghost.alpha.domain.model.SwarmSignal
import com.ghost.alpha.domain.model.TradeExecutionRequest
import com.ghost.alpha.domain.model.TradeExecutionResult
import com.ghost.alpha.domain.repository.MarketRepository
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class MarketRepositoryImpl @Inject constructor(
    private val apiService: GhostAlphaApiService,
    private val signalDao: SignalDao,
    private val positionDao: PositionDao,
    private val tradeHistoryDao: TradeHistoryDao
) : MarketRepository {
    override fun observeCachedSignals(): Flow<List<Signal>> = signalDao.observeAll().map { rows ->
        rows.map { it.toDomain() }
    }

    override fun observeCachedPositions(): Flow<List<Position>> = positionDao.observeAll().map { rows ->
        rows.map { it.toDomain() }
    }

    override suspend fun fetchSignal(symbol: String): Signal {
        val signal = apiService.getSignal(symbol).toDomain()
        signalDao.upsert(signal.toEntity())
        return signal
    }

    override suspend fun fetchPortfolio(): PortfolioSnapshot {
        val portfolio = apiService.getPortfolio().toDomain()
        positionDao.clear()
        positionDao.replaceAll(portfolio.positions.map { it.toEntity() })
        return portfolio
    }

    override suspend fun fetchSwarmSignal(symbol: String): SwarmSignal {
        return apiService.getSwarm(symbol).toDomain()
    }

    override suspend fun executeTrade(request: TradeExecutionRequest): TradeExecutionResult {
        val result = apiService.executeTrade(request.toDto()).toDomain()
        tradeHistoryDao.insert(result.toEntity(request.symbol, request.strategy, request.side))
        return result
    }

    override suspend fun runBacktest(request: BacktestRequest): BacktestResult {
        return apiService.runBacktest(request.toDto()).toDomain()
    }
}