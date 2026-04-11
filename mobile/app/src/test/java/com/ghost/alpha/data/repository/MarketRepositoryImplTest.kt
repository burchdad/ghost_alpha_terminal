package com.ghost.alpha.data.repository

import com.ghost.alpha.data.local.PositionDao
import com.ghost.alpha.data.local.SignalDao
import com.ghost.alpha.data.local.TradeHistoryDao
import com.ghost.alpha.data.remote.ConsensusDto
import com.ghost.alpha.data.remote.ExecuteTradeResponseDto
import com.ghost.alpha.data.remote.GhostAlphaApiService
import com.ghost.alpha.data.remote.PortfolioDto
import com.ghost.alpha.data.remote.PositionDto
import com.ghost.alpha.data.remote.SignalDto
import com.ghost.alpha.data.remote.SwarmResponseDto
import com.ghost.alpha.domain.model.TradeExecutionRequest
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.every
import io.mockk.just
import io.mockk.mockk
import io.mockk.runs
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant

class MarketRepositoryImplTest {
    private val apiService = mockk<GhostAlphaApiService>()
    private val signalDao = mockk<SignalDao>()
    private val positionDao = mockk<PositionDao>()
    private val tradeHistoryDao = mockk<TradeHistoryDao>()

    private val repository = MarketRepositoryImpl(apiService, signalDao, positionDao, tradeHistoryDao)

    @Test
    fun fetchSignalPersistsAndReturnsDomainSignal() = runTest {
        coEvery { apiService.getSignal("AAPL") } returns SignalDto(
            symbol = "AAPL",
            signal = "BUY",
            confidence = 0.82,
            reasoning = "Momentum",
            generatedAt = Instant.now().toString()
        )
        coEvery { signalDao.upsert(any()) } just runs

        val result = repository.fetchSignal("AAPL")

        assertEquals("AAPL", result.symbol)
        assertEquals("BUY", result.signal)
        coVerify(exactly = 1) { signalDao.upsert(any()) }
    }

    @Test
    fun fetchPortfolioReplacesCachedPositions() = runTest {
        coEvery { apiService.getPortfolio() } returns PortfolioDto(
            accountBalance = 100000.0,
            activePositions = listOf(
                PositionDto(
                    symbol = "AAPL",
                    side = "LONG",
                    entryPrice = 190.0,
                    currentPrice = 192.0,
                    unrealizedPnl = 2.0,
                    unrealizedPnlPct = 0.01,
                    units = 10.0,
                    notional = 1920.0,
                    openedAt = Instant.now().toString()
                )
            ),
            totalExposure = 1920.0,
            riskExposurePct = 0.02,
            availableBuyingPower = 98080.0,
            maxConcurrentTrades = 8
        )
        coEvery { positionDao.clear() } just runs
        coEvery { positionDao.replaceAll(any()) } just runs

        val result = repository.fetchPortfolio()

        assertEquals(100000.0, result.accountBalance, 0.0)
        assertEquals(1, result.positions.size)
        coVerify(exactly = 1) { positionDao.clear() }
        coVerify(exactly = 1) { positionDao.replaceAll(any()) }
    }

    @Test
    fun executeTradeStoresTradeHistory() = runTest {
        coEvery { apiService.executeTrade(any()) } returns ExecuteTradeResponseDto(
            accepted = true,
            riskLevel = "LOW",
            positionSize = 1.5,
            expectedValue = 1.2
        )
        coEvery { tradeHistoryDao.insert(any()) } just runs

        val result = repository.executeTrade(
            TradeExecutionRequest(
                symbol = "AAPL",
                strategy = "swarm_consensus",
                side = "LONG",
                entryPrice = 190.0,
                stopLossPct = 0.02,
                takeProfitPct = 0.03,
                accountBalance = 100000.0,
                riskPerTrade = 0.01,
                confidence = 0.7
            )
        )

        assertTrue(result.accepted)
        coVerify(exactly = 1) { tradeHistoryDao.insert(any()) }
    }

    @Test
    fun fetchSwarmSignalMapsResponse() = runTest {
        coEvery { apiService.getSwarm("AAPL") } returns SwarmResponseDto(
            symbol = "AAPL",
            regime = "TREND",
            regimeConfidence = 0.8,
            consensus = ConsensusDto(finalBias = "BUY", confidence = 0.73, topStrategy = "swarm"),
            agentBreakdown = emptyList(),
            riskLevel = "LOW",
            expectedValue = 1.6,
            generatedAt = Instant.now().toString()
        )

        val result = repository.fetchSwarmSignal("AAPL")

        assertEquals("AAPL", result.symbol)
        assertEquals("BUY", result.signal)
    }

    @Test
    fun observeCachedStreamsWireToDaos() {
        every { signalDao.observeAll() } returns emptyFlow()
        every { positionDao.observeAll() } returns emptyFlow()

        repository.observeCachedSignals()
        repository.observeCachedPositions()

        coVerify(exactly = 0) { apiService.getSignal(any()) }
    }
}
