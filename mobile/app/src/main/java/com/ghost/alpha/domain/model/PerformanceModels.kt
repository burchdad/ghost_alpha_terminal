package com.ghost.alpha.domain.model

import java.time.Instant

data class StrategyPerformance(
    val strategy: String,
    val trades: Int,
    val winRate: Double,
    val netPnl: Double
)

data class AgentWeight(
    val agentName: String,
    val weight: Double,
    val rawScore: Double
)

data class RegimeWeightSet(
    val regime: String,
    val agents: List<AgentWeight>
)

data class ExecutionPerformanceItem(
    val executionId: String,
    val symbol: String,
    val strategy: String,
    val confidence: Double,
    val submitted: Boolean,
    val outcomeLabel: String?,
    val pnl: Double?,
    val timestamp: Instant
)

data class AgentLeaderboardItem(
    val agentName: String,
    val winRate: Double,
    val accuracy: Double,
    val compositeScore: Double
)

data class SymbolPerformanceInsight(
    val symbol: String,
    val bestAgent: String,
    val topAgents: List<AgentLeaderboardItem>,
    val topStrategies: List<StrategyPerformance>,
    val generatedAt: Instant
)

data class PerformanceIntelligenceSnapshot(
    val windowDays: Int,
    val asOf: Instant,
    val trades: Int,
    val settledTrades: Int,
    val winRate: Double,
    val netPnl: Double,
    val bestStrategy: StrategyPerformance?,
    val worstStrategy: StrategyPerformance?,
    val strategyBreakdown: List<StrategyPerformance>,
    val regimeWeights: List<RegimeWeightSet>,
    val recentExecutions: List<ExecutionPerformanceItem>,
    val symbolInsight: SymbolPerformanceInsight?
)
