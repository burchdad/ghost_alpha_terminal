package com.ghost.alpha.domain.model

import java.time.Instant

data class Signal(
    val symbol: String,
    val signal: String,
    val confidence: Double,
    val reasoning: String,
    val generatedAt: Instant
)

data class Position(
    val symbol: String,
    val strategy: String,
    val side: String,
    val entryPrice: Double,
    val currentPrice: Double,
    val unrealizedPnl: Double,
    val unrealizedPnlPct: Double,
    val units: Double,
    val notional: Double,
    val sector: String,
    val openedAt: Instant
)

data class Broker(
    val provider: String,
    val label: String,
    val connected: Boolean,
    val accounts: List<String>,
    val configured: Boolean = false,
    val planned: Boolean = false
)

data class AgentVote(
    val name: String,
    val bias: String,
    val confidence: Double,
    val reasoning: String,
    val weightedConfidence: Double?
)

data class SwarmSignal(
    val symbol: String,
    val signal: String,
    val confidence: Double,
    val regime: String,
    val regimeConfidence: Double,
    val topStrategy: String,
    val riskLevel: String,
    val expectedValue: Double,
    val agents: List<AgentVote>,
    val generatedAt: Instant
)

data class TradeExecutionRequest(
    val symbol: String,
    val strategy: String,
    val side: String,
    val entryPrice: Double,
    val stopLossPct: Double,
    val takeProfitPct: Double,
    val accountBalance: Double,
    val riskPerTrade: Double,
    val confidence: Double
)

data class TradeExecutionResult(
    val accepted: Boolean,
    val reason: String?,
    val positionSize: Double,
    val maxLossAmount: Double,
    val riskLevel: String,
    val expectedValue: Double,
    val riskRewardRatio: Double,
    val targetPct: Double,
    val positionNotional: Double,
    val governorDecision: String?,
    val governorReason: String?
)

data class BacktestRequest(
    val symbol: String,
    val timeframe: String,
    val startDate: Instant,
    val endDate: Instant,
    val initialCapital: Double,
    val riskPerTrade: Double,
    val takeProfitPct: Double,
    val stopLossPct: Double,
    val maxHoldPeriods: Int,
    val enableEvolution: Boolean,
    val enableCompounding: Boolean
)

data class SimulatedTrade(
    val strategy: String,
    val side: String,
    val entryPrice: Double,
    val exitPrice: Double,
    val pnl: Double,
    val outcome: String,
    val entryTime: Instant,
    val exitTime: Instant
)

data class EquityPoint(
    val timestamp: Instant,
    val equity: Double
)

data class BacktestResult(
    val symbol: String,
    val timeframe: String,
    val startingCapital: Double,
    val endingBalance: Double,
    val totalTrades: Int,
    val winRate: Double,
    val totalPnl: Double,
    val maxDrawdown: Double,
    val sharpeRatio: Double,
    val stabilityScore: Double,
    val equityCurve: List<EquityPoint>,
    val tradeHistory: List<SimulatedTrade>
)

data class PortfolioSnapshot(
    val accountBalance: Double,
    val positions: List<Position>,
    val totalExposure: Double,
    val riskExposurePct: Double,
    val availableBuyingPower: Double,
    val maxConcurrentTrades: Int
)

data class AlertItem(
    val id: String,
    val title: String,
    val message: String,
    val severity: String,
    val timestamp: Instant,
    val symbol: String? = null
)

data class DashboardSnapshot(
    val portfolio: PortfolioSnapshot,
    val featuredSignal: Signal?,
    val featuredSwarm: SwarmSignal?,
    val alerts: List<AlertItem>
)

data class RealtimeEvent(
    val channel: String,
    val type: String,
    val title: String,
    val message: String,
    val severity: String,
    val timestamp: Instant,
    val symbol: String? = null,
    val payload: Map<String, String> = emptyMap()
)