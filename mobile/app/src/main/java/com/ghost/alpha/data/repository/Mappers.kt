package com.ghost.alpha.data.repository

import com.ghost.alpha.data.remote.AuthResponseDto
import com.ghost.alpha.data.remote.BacktestResponseDto
import com.ghost.alpha.data.remote.BrokerStatusItemDto
import com.ghost.alpha.data.remote.ExecuteTradeRequestDto
import com.ghost.alpha.data.remote.ExecuteTradeResponseDto
import com.ghost.alpha.data.remote.PortfolioDto
import com.ghost.alpha.data.remote.PositionDto
import com.ghost.alpha.data.remote.SignalDto
import com.ghost.alpha.data.remote.SwarmResponseDto
import com.ghost.alpha.data.remote.UserDto
import com.ghost.alpha.domain.model.AgentVote
import com.ghost.alpha.domain.model.BacktestRequest
import com.ghost.alpha.domain.model.BacktestResult
import com.ghost.alpha.domain.model.Broker
import com.ghost.alpha.domain.model.EquityPoint
import com.ghost.alpha.domain.model.LoginResult
import com.ghost.alpha.domain.model.PortfolioSnapshot
import com.ghost.alpha.domain.model.Position
import com.ghost.alpha.domain.model.SessionState
import com.ghost.alpha.domain.model.Signal
import com.ghost.alpha.domain.model.SimulatedTrade
import com.ghost.alpha.domain.model.SwarmSignal
import com.ghost.alpha.domain.model.TokenBundle
import com.ghost.alpha.domain.model.TradeExecutionRequest
import com.ghost.alpha.domain.model.TradeExecutionResult
import com.ghost.alpha.domain.model.User
import java.time.Instant

fun UserDto.toDomain(highTrust: Boolean = false): User = User(
    id = id.orEmpty(),
    email = email.orEmpty(),
    displayName = fullName ?: email.orEmpty(),
    twoFactorEnabled = twoFaVerified == true || !twoFaMethod.isNullOrBlank(),
    highTrust = highTrust,
    stepUpRequired = stepUpRequired == true,
    riskScore = riskScore ?: 0,
    riskReasons = riskReasons.orEmpty()
)

fun AuthResponseDto.toLoginResult(): LoginResult {
    val tokens = if (!accessToken.isNullOrBlank() && !refreshToken.isNullOrBlank()) {
        TokenBundle(
            accessToken = accessToken,
            refreshToken = refreshToken,
            tokenType = tokenType ?: "Bearer",
            accessTokenExpiresAt = accessTokenExpiresAt?.let(Instant::parse),
            refreshTokenExpiresAt = refreshTokenExpiresAt?.let(Instant::parse)
        )
    } else {
        null
    }

    return LoginResult(
        session = SessionState(
            user = user?.toDomain(),
            tokens = tokens,
            isAuthenticated = user != null,
            pendingStepUpMethod = challengeMethod
        ),
        requiresTwoFactor = requiresTwoFactor == true || user?.stepUpRequired == true,
        challengeMethod = challengeMethod ?: user?.twoFaMethod
    )
}

fun AuthResponseDto.toSessionState(existing: SessionState?): SessionState {
    val tokens = if (!accessToken.isNullOrBlank() && !refreshToken.isNullOrBlank()) {
        TokenBundle(
            accessToken = accessToken,
            refreshToken = refreshToken,
            tokenType = tokenType ?: "Bearer",
            accessTokenExpiresAt = accessTokenExpiresAt?.let(Instant::parse),
            refreshTokenExpiresAt = refreshTokenExpiresAt?.let(Instant::parse)
        )
    } else {
        existing?.tokens
    }

    return SessionState(
        user = user?.toDomain(highTrust = existing?.user?.highTrust == true) ?: existing?.user,
        tokens = tokens,
        isAuthenticated = user != null || existing?.isAuthenticated == true,
        highTrustUntil = existing?.highTrustUntil,
        pendingStepUpMethod = challengeMethod ?: existing?.pendingStepUpMethod
    )
}

fun SignalDto.toDomain(): Signal = Signal(
    symbol = symbol,
    signal = signal,
    confidence = confidence,
    reasoning = reasoning,
    generatedAt = Instant.parse(generatedAt)
)

fun PositionDto.toDomain(): Position = Position(
    symbol = symbol,
    strategy = strategy,
    side = side,
    entryPrice = entryPrice,
    currentPrice = currentPrice,
    unrealizedPnl = unrealizedPnl,
    unrealizedPnlPct = unrealizedPnlPct,
    units = units,
    notional = notional,
    sector = sector,
    openedAt = Instant.parse(openedAt)
)

fun PortfolioDto.toDomain(): PortfolioSnapshot = PortfolioSnapshot(
    accountBalance = accountBalance,
    positions = activePositions.map(PositionDto::toDomain),
    totalExposure = totalExposure,
    riskExposurePct = riskExposurePct,
    availableBuyingPower = availableBuyingPower,
    maxConcurrentTrades = maxConcurrentTrades
)

fun SwarmResponseDto.toDomain(): SwarmSignal = SwarmSignal(
    symbol = symbol,
    signal = consensus.finalBias,
    confidence = consensus.confidence,
    regime = regime,
    regimeConfidence = regimeConfidence,
    topStrategy = consensus.topStrategy,
    riskLevel = riskLevel,
    expectedValue = expectedValue,
    agents = agentBreakdown.map {
        AgentVote(
            name = it.agentName,
            bias = it.bias,
            confidence = it.confidence,
            reasoning = it.reasoning,
            weightedConfidence = it.weightedConfidence
        )
    },
    generatedAt = Instant.parse(generatedAt)
)

fun TradeExecutionRequest.toDto(): ExecuteTradeRequestDto = ExecuteTradeRequestDto(
    symbol = symbol,
    strategy = strategy,
    side = side,
    entryPrice = entryPrice,
    stopLossPct = stopLossPct,
    takeProfitPct = takeProfitPct,
    accountBalance = accountBalance,
    riskPerTrade = riskPerTrade,
    confidence = confidence
)

fun ExecuteTradeResponseDto.toDomain(): TradeExecutionResult = TradeExecutionResult(
    accepted = accepted,
    reason = reason,
    positionSize = positionSize,
    maxLossAmount = maxLossAmount,
    riskLevel = riskLevel,
    expectedValue = expectedValue,
    riskRewardRatio = riskRewardRatio,
    targetPct = targetPct,
    positionNotional = positionNotional,
    governorDecision = governorDecision,
    governorReason = governorReason
)

fun Pair<String, BrokerStatusItemDto>.toDomain(): Broker = Broker(
    provider = first,
    label = second.label.ifBlank { first.replaceFirstChar(Char::uppercase) },
    connected = second.connected,
    accounts = second.accounts,
    configured = second.configured,
    planned = second.planned
)

fun BacktestRequest.toDto(): com.ghost.alpha.data.remote.BacktestRequestDto = com.ghost.alpha.data.remote.BacktestRequestDto(
    symbol = symbol,
    timeframe = timeframe,
    startDate = startDate.toString(),
    endDate = endDate.toString(),
    initialCapital = initialCapital,
    riskPerTrade = riskPerTrade,
    takeProfitPct = takeProfitPct,
    stopLossPct = stopLossPct,
    maxHoldPeriods = maxHoldPeriods,
    enableEvolution = enableEvolution,
    enableCompounding = enableCompounding
)

fun BacktestResponseDto.toDomain(): BacktestResult = BacktestResult(
    symbol = symbol,
    timeframe = timeframe,
    startingCapital = startingCapital,
    endingBalance = endingBalance,
    totalTrades = totalTrades,
    winRate = winRate,
    totalPnl = totalPnl,
    maxDrawdown = maxDrawdown,
    sharpeRatio = sharpeRatio,
    stabilityScore = stabilityScore,
    equityCurve = equityCurve.map { EquityPoint(timestamp = Instant.parse(it.timestamp), equity = it.equity) },
    tradeHistory = tradeHistory.map {
        SimulatedTrade(
            strategy = it.strategy,
            side = it.side,
            entryPrice = it.entryPrice,
            exitPrice = it.exitPrice,
            pnl = it.pnl,
            outcome = it.outcome,
            entryTime = Instant.parse(it.entryTime),
            exitTime = Instant.parse(it.exitTime)
        )
    }
)