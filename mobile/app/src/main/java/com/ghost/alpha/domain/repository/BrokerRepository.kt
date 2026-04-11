package com.ghost.alpha.domain.repository

import com.ghost.alpha.domain.model.Broker

interface BrokerRepository {
    suspend fun fetchBrokers(): List<Broker>
    fun buildConnectUrl(provider: String): String
    suspend fun disconnect(provider: String): Boolean
}