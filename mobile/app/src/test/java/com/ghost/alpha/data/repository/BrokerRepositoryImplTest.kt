package com.ghost.alpha.data.repository

import com.ghost.alpha.BuildConfig
import com.ghost.alpha.data.remote.BrokerStatusItemDto
import com.ghost.alpha.data.remote.GhostAlphaApiService
import io.mockk.coEvery
import io.mockk.coVerify
import io.mockk.mockk
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class BrokerRepositoryImplTest {
    private val apiService = mockk<GhostAlphaApiService>()
    private val repository = BrokerRepositoryImpl(apiService)

    @Test
    fun fetchBrokersReturnsSortedDomainList() = runTest {
        coEvery { apiService.getBrokers() } returns mapOf(
            "alpaca" to BrokerStatusItemDto(connected = true, label = "Alpaca", configured = true),
            "coinbase" to BrokerStatusItemDto(connected = false, label = "Coinbase", configured = true)
        )

        val brokers = repository.fetchBrokers()

        assertEquals(2, brokers.size)
        assertEquals("Alpaca", brokers.first().label)
        assertEquals("Coinbase", brokers.last().label)
    }

    @Test
    fun buildConnectUrlBuildsAlpacaOauthUrl() {
        val url = repository.buildConnectUrl("alpaca")

        assertTrue(url.startsWith(BuildConfig.API_BASE_URL))
        assertTrue(url.contains("alpaca/oauth/start"))
        assertTrue(url.contains("next="))
    }

    @Test
    fun disconnectReturnsTrueWhenApiSucceeds() = runTest {
        coEvery { apiService.disconnectAlpaca() } returns mapOf("ok" to true)

        val result = repository.disconnect("alpaca")

        assertTrue(result)
        coVerify(exactly = 1) { apiService.disconnectAlpaca() }
    }

    @Test
    fun disconnectReturnsFalseForUnknownProvider() = runTest {
        val result = repository.disconnect("coinbase")

        assertFalse(result)
    }
}
