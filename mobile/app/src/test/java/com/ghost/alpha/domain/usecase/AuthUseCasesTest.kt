package com.ghost.alpha.domain.usecase

import com.ghost.alpha.domain.model.LoginResult
import com.ghost.alpha.domain.model.SessionState
import com.ghost.alpha.domain.model.TwoFactorResult
import com.ghost.alpha.domain.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import java.time.Instant

class AuthUseCasesTest {
    private val fakeRepository = FakeAuthRepository()

    @Test
    fun loginUseCaseDelegatesToRepository() = runTest {
        val useCase = LoginUseCase(fakeRepository)

        val result = useCase("ops@ghostalpha.ai", "secure-pass")

        assertTrue(result.session.isAuthenticated)
        assertEquals("ops@ghostalpha.ai", fakeRepository.lastLoginEmail)
    }

    @Test
    fun refreshUseCaseDelegatesToRepository() = runTest {
        val useCase = RefreshTokenUseCase(fakeRepository)

        val result = useCase()

        assertTrue(result.isAuthenticated)
        assertTrue(fakeRepository.refreshInvoked)
    }

    @Test
    fun verifyTwoFactorUseCaseDelegatesToRepository() = runTest {
        val useCase = VerifyTwoFactorUseCase(fakeRepository)

        val result = useCase("123456", true)

        assertTrue(result.success)
        assertEquals("123456", fakeRepository.lastOtpCode)
    }

    private class FakeAuthRepository : AuthRepository {
        override val session = MutableStateFlow(SessionState())
        var lastLoginEmail: String? = null
        var lastOtpCode: String? = null
        var refreshInvoked: Boolean = false

        override suspend fun login(email: String, password: String): LoginResult {
            lastLoginEmail = email
            val state = SessionState(isAuthenticated = true)
            session.value = state
            return LoginResult(session = state, requiresTwoFactor = false)
        }

        override suspend fun refreshSession(): SessionState {
            refreshInvoked = true
            val state = SessionState(isAuthenticated = true)
            session.value = state
            return state
        }

        override suspend fun verifyTwoFactor(code: String, trustDevice: Boolean): TwoFactorResult {
            lastOtpCode = code
            return TwoFactorResult(
                success = true,
                highTrustUntil = Instant.now(),
                method = "totp",
                trustedDevice = trustDevice
            )
        }

        override suspend fun logout() {
            session.value = SessionState()
        }
    }
}
