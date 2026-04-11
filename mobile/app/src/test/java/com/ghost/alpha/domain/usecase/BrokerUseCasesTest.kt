package com.ghost.alpha.domain.usecase

import com.ghost.alpha.domain.model.Broker
import com.ghost.alpha.domain.repository.BrokerRepository
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class BrokerUseCasesTest {
    private val fakeRepository = FakeBrokerRepository()

    @Test
    fun fetchBrokersUseCaseReturnsList() = runTest {
        val useCase = FetchBrokersUseCase(fakeRepository)

        val result = useCase()

        assertEquals(1, result.size)
        assertEquals("alpaca", result.first().provider)
    }

    @Test
    fun connectBrokerUseCaseReturnsConnectUrl() {
        val useCase = ConnectBrokerUseCase(fakeRepository)

        val url = useCase("alpaca")

        assertTrue(url.contains("/connect/alpaca"))
    }

    @Test
    fun disconnectBrokerUseCaseDelegatesToRepository() = runTest {
        val useCase = DisconnectBrokerUseCase(fakeRepository)

        val result = useCase("alpaca")

        assertTrue(result)
        assertEquals("alpaca", fakeRepository.lastDisconnected)
    }

    private class FakeBrokerRepository : BrokerRepository {
        var lastDisconnected: String? = null

        override suspend fun fetchBrokers(): List<Broker> {
            return listOf(
                Broker(
                    provider = "alpaca",
                    label = "Alpaca",
                    connected = true,
                    accounts = listOf("paper")
                )
            )
        }

        override fun buildConnectUrl(provider: String): String = "https://api.ghostalpha.ai/connect/$provider"

        override suspend fun disconnect(provider: String): Boolean {
            lastDisconnected = provider
            return true
        }
    }
}
