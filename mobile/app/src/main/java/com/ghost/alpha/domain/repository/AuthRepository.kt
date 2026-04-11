package com.ghost.alpha.domain.repository

import com.ghost.alpha.domain.model.LoginResult
import com.ghost.alpha.domain.model.SessionState
import com.ghost.alpha.domain.model.TwoFactorResult
import kotlinx.coroutines.flow.StateFlow

interface AuthRepository {
    val session: StateFlow<SessionState>

    suspend fun login(email: String, password: String): LoginResult
    suspend fun refreshSession(): SessionState
    suspend fun verifyTwoFactor(code: String, trustDevice: Boolean): TwoFactorResult
    suspend fun logout()
}