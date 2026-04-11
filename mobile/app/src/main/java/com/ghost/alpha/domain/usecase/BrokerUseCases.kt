package com.ghost.alpha.domain.usecase

import com.ghost.alpha.domain.repository.BrokerRepository
import javax.inject.Inject

class FetchBrokersUseCase @Inject constructor(
    private val brokerRepository: BrokerRepository
) {
    suspend operator fun invoke() = brokerRepository.fetchBrokers()
}

class ConnectBrokerUseCase @Inject constructor(
    private val brokerRepository: BrokerRepository
) {
    operator fun invoke(provider: String) = brokerRepository.buildConnectUrl(provider)
}

class DisconnectBrokerUseCase @Inject constructor(
    private val brokerRepository: BrokerRepository
) {
    suspend operator fun invoke(provider: String) = brokerRepository.disconnect(provider)
}