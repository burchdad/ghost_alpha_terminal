package com.ghost.alpha.data.repository

import com.ghost.alpha.BuildConfig
import com.ghost.alpha.data.remote.GhostAlphaApiService
import com.ghost.alpha.domain.model.Broker
import com.ghost.alpha.domain.repository.BrokerRepository
import java.net.URLEncoder
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class BrokerRepositoryImpl @Inject constructor(
    private val apiService: GhostAlphaApiService
) : BrokerRepository {
    override suspend fun fetchBrokers(): List<Broker> {
        return apiService.getBrokers().entries.map { it.toPair().toDomain() }.sortedBy { it.label }
    }

    override fun buildConnectUrl(provider: String): String {
        val callback = "${BuildConfig.OAUTH_CALLBACK_SCHEME}://${BuildConfig.OAUTH_CALLBACK_HOST}${BuildConfig.OAUTH_CALLBACK_PATH}"
        val encoded = URLEncoder.encode(callback, Charsets.UTF_8.name())
        return when (provider.lowercase()) {
            "alpaca" -> "${BuildConfig.API_BASE_URL}alpaca/oauth/start?next=$encoded"
            else -> "${BuildConfig.API_BASE_URL}brokers/status"
        }
    }

    override suspend fun disconnect(provider: String): Boolean {
        return when (provider.lowercase()) {
            "alpaca" -> runCatching { apiService.disconnectAlpaca(); true }.getOrDefault(false)
            else -> false
        }
    }
}