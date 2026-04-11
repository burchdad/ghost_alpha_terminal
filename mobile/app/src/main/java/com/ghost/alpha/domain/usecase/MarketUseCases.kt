package com.ghost.alpha.domain.usecase

import com.ghost.alpha.domain.model.BacktestRequest
import com.ghost.alpha.domain.model.TradeExecutionRequest
import com.ghost.alpha.domain.repository.MarketRepository
import javax.inject.Inject

class FetchSignalsUseCase @Inject constructor(
    private val marketRepository: MarketRepository
) {
    suspend operator fun invoke(symbol: String) = marketRepository.fetchSignal(symbol)
}

class FetchPortfolioUseCase @Inject constructor(
    private val marketRepository: MarketRepository
) {
    suspend operator fun invoke() = marketRepository.fetchPortfolio()
}

class FetchSwarmSignalsUseCase @Inject constructor(
    private val marketRepository: MarketRepository
) {
    suspend operator fun invoke(symbol: String) = marketRepository.fetchSwarmSignal(symbol)
}

class ExecuteTradeUseCase @Inject constructor(
    private val marketRepository: MarketRepository
) {
    suspend operator fun invoke(request: TradeExecutionRequest) = marketRepository.executeTrade(request)
}

class RunBacktestUseCase @Inject constructor(
    private val marketRepository: MarketRepository
) {
    suspend operator fun invoke(request: BacktestRequest) = marketRepository.runBacktest(request)
}