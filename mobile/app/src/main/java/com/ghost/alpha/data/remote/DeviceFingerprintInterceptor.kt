package com.ghost.alpha.data.remote

import com.ghost.alpha.utils.DeviceFingerprintProvider
import okhttp3.Interceptor
import okhttp3.Response
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DeviceFingerprintInterceptor @Inject constructor(
    private val fingerprintProvider: DeviceFingerprintProvider
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val updated = chain.request().newBuilder()
            .header("X-Device-Fingerprint", fingerprintProvider.fingerprint())
            .header("X-Device-Risk-Signal", fingerprintProvider.riskSignal())
            .build()
        return chain.proceed(updated)
    }
}
