package com.ghost.alpha.data.local

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.ghost.alpha.domain.model.TokenBundle
import dagger.hilt.android.qualifiers.ApplicationContext
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AuthTokenStorage @Inject constructor(
    @ApplicationContext context: Context
) {
    private val prefs = EncryptedSharedPreferences.create(
        context,
        FILE_NAME,
        MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build(),
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
    )

    fun read(): TokenBundle? {
        val accessToken = prefs.getString(KEY_ACCESS_TOKEN, null) ?: return null
        val refreshToken = prefs.getString(KEY_REFRESH_TOKEN, null) ?: return null
        return TokenBundle(
            accessToken = accessToken,
            refreshToken = refreshToken,
            tokenType = prefs.getString(KEY_TOKEN_TYPE, "Bearer") ?: "Bearer",
            accessTokenExpiresAt = prefs.getString(KEY_ACCESS_EXPIRY, null)?.let(Instant::parse),
            refreshTokenExpiresAt = prefs.getString(KEY_REFRESH_EXPIRY, null)?.let(Instant::parse)
        )
    }

    fun write(bundle: TokenBundle) {
        prefs.edit()
            .putString(KEY_ACCESS_TOKEN, bundle.accessToken)
            .putString(KEY_REFRESH_TOKEN, bundle.refreshToken)
            .putString(KEY_TOKEN_TYPE, bundle.tokenType)
            .putString(KEY_ACCESS_EXPIRY, bundle.accessTokenExpiresAt?.toString())
            .putString(KEY_REFRESH_EXPIRY, bundle.refreshTokenExpiresAt?.toString())
            .apply()
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    companion object {
        private const val FILE_NAME = "ghost_alpha_secure_session"
        private const val KEY_ACCESS_TOKEN = "access_token"
        private const val KEY_REFRESH_TOKEN = "refresh_token"
        private const val KEY_TOKEN_TYPE = "token_type"
        private const val KEY_ACCESS_EXPIRY = "access_token_expiry"
        private const val KEY_REFRESH_EXPIRY = "refresh_token_expiry"
    }
}