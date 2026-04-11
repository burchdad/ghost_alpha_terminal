package com.ghost.alpha.data.repository

import com.ghost.alpha.data.remote.GhostAlphaApiService
import com.ghost.alpha.domain.model.AgentLeaderboardItem
import com.ghost.alpha.domain.model.AgentWeight
import com.ghost.alpha.domain.model.ExecutionPerformanceItem
import com.ghost.alpha.domain.model.PerformanceIntelligenceSnapshot
import com.ghost.alpha.domain.model.RegimeWeightSet
import com.ghost.alpha.domain.model.StrategyPerformance
import com.ghost.alpha.domain.model.SymbolPerformanceInsight
import com.ghost.alpha.domain.repository.PerformanceRepository
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class PerformanceRepositoryImpl @Inject constructor(
    private val apiService: GhostAlphaApiService
) : PerformanceRepository {

    override suspend fun getPerformanceIntelligence(days: Int, symbol: String): PerformanceIntelligenceSnapshot {
        val truth = apiService.getTruthDashboard(days = days)
        val weights = apiService.getAgentWeights()
        val executions = apiService.getExecutionHistory(limit = 50)
        val symbolPerformance = runCatching { apiService.getSymbolPerformance(symbol) }.getOrNull()

        return PerformanceIntelligenceSnapshot(
            windowDays = truth.windowDays,
            asOf = parseInstant(truth.asOf),
            trades = truth.trades,
            settledTrades = truth.settledTrades,
            winRate = truth.winRate,
            netPnl = truth.netPnl,
            bestStrategy = truth.bestStrategy?.let {
                StrategyPerformance(
                    strategy = it.strategy,
                    trades = it.trades,
                    winRate = it.winRate,
                    netPnl = it.netPnl
                )
            },
            worstStrategy = truth.worstStrategy?.let {
                StrategyPerformance(
                    strategy = it.strategy,
                    trades = it.trades,
                    winRate = it.winRate,
                    netPnl = it.netPnl
                )
            },
            strategyBreakdown = truth.strategyBreakdown.map {
                StrategyPerformance(
                    strategy = it.strategy,
                    trades = it.trades,
                    winRate = it.winRate,
                    netPnl = it.netPnl
                )
            },
            regimeWeights = weights.regimeWeights.entries.map { (regime, entries) ->
                RegimeWeightSet(
                    regime = regime,
                    agents = entries.map { AgentWeight(it.agentName, it.weight, it.rawScore) }
                )
            },
            recentExecutions = executions.executions.map {
                ExecutionPerformanceItem(
                    executionId = it.executionId,
                    symbol = it.symbol,
                    strategy = it.strategy,
                    confidence = it.confidence,
                    submitted = it.submitted,
                    outcomeLabel = it.outcomeLabel,
                    pnl = it.pnl,
                    timestamp = parseInstant(it.timestamp)
                )
            },
            symbolInsight = symbolPerformance?.let {
                SymbolPerformanceInsight(
                    symbol = it.symbol,
                    bestAgent = it.bestAgent,
                    topAgents = it.agentLeaderboard.map { row ->
                        AgentLeaderboardItem(
                            agentName = row.agentName,
                            winRate = row.winRate,
                            accuracy = row.accuracy,
                            compositeScore = row.compositeScore
                        )
                    },
                    topStrategies = it.topStrategies.map { s ->
                        StrategyPerformance(
                            strategy = s.strategy,
                            trades = s.trades,
                            winRate = s.winRate,
                            netPnl = s.avgPnl
                        )
                    },
                    generatedAt = parseInstant(it.generatedAt)
                )
            }
        )
    }

    private fun parseInstant(value: String): Instant = runCatching { Instant.parse(value) }.getOrDefault(Instant.now())
}
