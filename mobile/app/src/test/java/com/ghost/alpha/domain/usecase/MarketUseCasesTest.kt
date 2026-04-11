package com.ghost.alpha.domain.usecase

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
import kotlinx.coroutines.flow.emptyFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant

class MarketUseCasesTest {
    private val fakeRepository = FakeMarketRepository()

    @Test
    fun fetchSignalsUseCaseReturnsRepositorySignal() = runTest {
        val useCase = FetchSignalsUseCase(fakeRepository)

        val result = useCase("AAPL")

        assertEquals("AAPL", result.symbol)
        assertEquals("AAPL", fakeRepository.lastSymbol)
    }

    @Test
    fun executeTradeUseCaseDelegatesToRepository() = runTest {
        val useCase = ExecuteTradeUseCase(fakeRepository)

        val result = useCase(
            TradeExecutionRequest(
                symbol = "AAPL",
                strategy = "swarm",
                side = "LONG",
                entryPrice = 100.0,
                stopLossPct = 0.02,
                takeProfitPct = 0.03,
                accountBalance = 100000.0,
                riskPerTrade = 0.01,
                confidence = 0.7
            )
        )

        assertTrue(result.accepted)
        assertEquals("AAPL", fakeRepository.lastTradeSymbol)
    }

    @Test
    fun runBacktestUseCaseDelegatesToRepository() = runTest {
        val useCase = RunBacktestUseCase(fakeRepository)

        val result = useCase(
            BacktestRequest(
                symbol = "AAPL",
                timeframe = "1d",
                startDate = Instant.now().minusSeconds(86400 * 30),
                endDate = Instant.now(),
                initialCapital = 100000.0,
                riskPerTrade = 0.01,
                takeProfitPct = 0.03,
                stopLossPct = 0.02,
                maxHoldPeriods = 5,
                enableEvolution = true,
                enableCompounding = true
            )
        )

        assertEquals("AAPL", result.symbol)
    }

    private class FakeMarketRepository : MarketRepository {
        var lastSymbol: String? = null
        var lastTradeSymbol: String? = null

        override fun observeCachedSignals(): Flow<List<Signal>> = emptyFlow()

        override fun observeCachedPositions(): Flow<List<Position>> = emptyFlow()

        override suspend fun fetchSignal(symbol: String): Signal {
            lastSymbol = symbol
            return Signal(symbol, "BUY", 0.78, "Momentum breakout", Instant.now())
        }

        override suspend fun fetchPortfolio(): PortfolioSnapshot {
            return PortfolioSnapshot(
                accountBalance = 100000.0,
                positions = emptyList(),
                totalExposure = 0.0,
                riskExposurePct = 0.0,
                availableBuyingPower = 100000.0,
                maxConcurrentTrades = 6
            )
        }

        override suspend fun fetchSwarmSignal(symbol: String): SwarmSignal {
            return SwarmSignal(
                symbol = symbol,
                signal = "BUY",
                confidence = 0.74,
                regime = "TREND",
                regimeConfidence = 0.7,
                topStrategy = "swarm",
                riskLevel = "MEDIUM",
                expectedValue = 1.2,
                agents = emptyList(),
                generatedAt = Instant.now()
            )
        }

        override suspend fun executeTrade(request: TradeExecutionRequest): TradeExecutionResult {
            lastTradeSymbol = request.symbol
            return TradeExecutionResult(
                accepted = true,
                reason = null,
                positionSize = 1.0,
                maxLossAmount = 100.0,
                riskLevel = "LOW",
                expectedValue = 1.5,
                riskRewardRatio = 2.0,
                targetPct = 0.03,
                positionNotional = 100.0,
                governorDecision = "allow",
                governorReason = null
            )
        }

        override suspend fun runBacktest(request: BacktestRequest): BacktestResult {
            return BacktestResult(
                symbol = request.symbol,
                timeframe = request.timeframe,
                startingCapital = request.initialCapital,
                endingBalance = request.initialCapital + 1000.0,
                totalTrades = 10,
                winRate = 0.6,
                totalPnl = 1000.0,
                maxDrawdown = 0.05,
                sharpeRatio = 1.3,
                stabilityScore = 0.7,
                equityCurve = emptyList(),
                tradeHistory = emptyList()
            )
        }
    }
}
