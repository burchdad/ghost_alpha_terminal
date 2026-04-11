package com.ghost.alpha.data.repository

import com.ghost.alpha.data.local.AuthTokenStorage
import com.ghost.alpha.data.remote.GhostAlphaApiService
import com.ghost.alpha.data.remote.TwoFactorVerifyRequestDto
import com.ghost.alpha.domain.model.SessionState
import com.ghost.alpha.domain.model.TwoFactorResult
import com.ghost.alpha.domain.repository.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthRepositoryImpl @Inject constructor(
    private val apiService: GhostAlphaApiService,
    private val tokenStorage: AuthTokenStorage
) : AuthRepository {
    private val _session = MutableStateFlow(
        SessionState(tokens = tokenStorage.read(), isAuthenticated = tokenStorage.read() != null)
    )
    override val session: StateFlow<SessionState> = _session.asStateFlow()

    override suspend fun login(email: String, password: String) = apiService.login(
        com.ghost.alpha.data.remote.LoginRequestDto(email = email, password = password)
    ).toLoginResult().also { result ->
        result.session.tokens?.let(tokenStorage::write)
        _session.value = result.session
    }

    override suspend fun refreshSession(): SessionState {
        val refreshed = apiService.refreshSession().toSessionState(_session.value)
        refreshed.tokens?.let(tokenStorage::write)
        _session.value = refreshed
        return refreshed
    }

    override suspend fun verifyTwoFactor(code: String, trustDevice: Boolean): TwoFactorResult {
        val response = apiService.verifyTwoFactor(
            TwoFactorVerifyRequestDto(code = code, trustDevice = trustDevice)
        )
        val updated = _session.value.copy(
            user = _session.value.user?.copy(highTrust = response.success, stepUpRequired = false),
            highTrustUntil = response.highTrustUntil?.let(Instant::parse),
            pendingStepUpMethod = null
        )
        _session.value = updated
        return TwoFactorResult(
            success = response.success,
            highTrustUntil = response.highTrustUntil?.let(Instant::parse),
            method = response.method,
            trustedDevice = response.trustedDevice
        )
    }

    override suspend fun logout() {
        runCatching { apiService.logout() }
        tokenStorage.clear()
        _session.value = SessionState()
    }
}