package com.ghost.alpha.data.remote

import com.ghost.alpha.data.local.AuthTokenStorage
import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route
import java.time.Instant
import javax.inject.Inject
import javax.inject.Provider
import javax.inject.Singleton

@Singleton
class TokenRefreshAuthenticator @Inject constructor(
    private val tokenStorage: AuthTokenStorage,
    private val apiProvider: Provider<GhostAlphaApiService>
) : Authenticator {
    override fun authenticate(route: Route?, response: Response): Request? {
        if (responseCount(response) >= 2) {
            return null
        }

        synchronized(this) {
            val currentTokens = tokenStorage.read() ?: return null
            return try {
                val refreshed = apiProvider.get().refreshSession()
                val accessToken = refreshed.accessToken ?: currentTokens.accessToken
                val refreshToken = refreshed.refreshToken ?: currentTokens.refreshToken
                tokenStorage.write(
                    currentTokens.copy(
                        accessToken = accessToken,
                        refreshToken = refreshToken,
                        tokenType = refreshed.tokenType ?: currentTokens.tokenType,
                        accessTokenExpiresAt = refreshed.accessTokenExpiresAt?.let(Instant::parse)
                            ?: currentTokens.accessTokenExpiresAt,
                        refreshTokenExpiresAt = refreshed.refreshTokenExpiresAt?.let(Instant::parse)
                            ?: currentTokens.refreshTokenExpiresAt
                    )
                )
                response.request.newBuilder()
                    .header("Authorization", "${refreshed.tokenType ?: currentTokens.tokenType} $accessToken")
                    .build()
            } catch (_: Exception) {
                tokenStorage.clear()
                null
            }
        }
    }

    private fun responseCount(response: Response): Int {
        var current = response.priorResponse
        var result = 1
        while (current != null) {
            result += 1
            current = current.priorResponse
        }
        return result
    }
}