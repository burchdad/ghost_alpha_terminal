package com.ghost.alpha.data.remote

import com.ghost.alpha.data.local.AuthTokenStorage
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AccessTokenInterceptor @Inject constructor(
    private val tokenStorage: AuthTokenStorage
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val currentRequest = chain.request()
        val tokenBundle = tokenStorage.read()
        if (tokenBundle == null) {
            return chain.proceed(currentRequest)
        }

        val updatedRequest = currentRequest.newBuilder()
            .header("Authorization", "${tokenBundle.tokenType} ${tokenBundle.accessToken}")
            .build()

        return chain.proceed(updatedRequest)
    }
}