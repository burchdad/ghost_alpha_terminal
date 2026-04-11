package com.ghost.alpha.domain.usecase

import com.ghost.alpha.domain.repository.AuthRepository
import javax.inject.Inject

class LoginUseCase @Inject constructor(
    private val authRepository: AuthRepository
) {
    suspend operator fun invoke(email: String, password: String) = authRepository.login(email, password)
}

class RefreshTokenUseCase @Inject constructor(
    private val authRepository: AuthRepository
) {
    suspend operator fun invoke() = authRepository.refreshSession()
}

class VerifyTwoFactorUseCase @Inject constructor(
    private val authRepository: AuthRepository
) {
    suspend operator fun invoke(code: String, trustDevice: Boolean) = authRepository.verifyTwoFactor(code, trustDevice)
}