package com.ghost.alpha.domain.model

import java.time.Instant

data class User(
    val id: String,
    val email: String,
    val displayName: String,
    val twoFactorEnabled: Boolean,
    val highTrust: Boolean = false,
    val stepUpRequired: Boolean = false,
    val riskScore: Int = 0,
    val riskReasons: List<String> = emptyList()
)

data class TokenBundle(
    val accessToken: String,
    val refreshToken: String,
    val tokenType: String = "Bearer",
    val accessTokenExpiresAt: Instant? = null,
    val refreshTokenExpiresAt: Instant? = null
)

data class SessionState(
    val user: User? = null,
    val tokens: TokenBundle? = null,
    val isAuthenticated: Boolean = false,
    val highTrustUntil: Instant? = null,
    val pendingStepUpMethod: String? = null
)

data class LoginResult(
    val session: SessionState,
    val requiresTwoFactor: Boolean,
    val challengeMethod: String? = null
)

data class TwoFactorResult(
    val success: Boolean,
    val highTrustUntil: Instant?,
    val method: String?,
    val trustedDevice: Boolean
)