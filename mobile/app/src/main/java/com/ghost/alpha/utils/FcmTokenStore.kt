package com.ghost.alpha.utils

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class FcmTokenStore @Inject constructor(
    @ApplicationContext context: Context
) {
    private val prefs = context.getSharedPreferences("ghost_alpha_fcm", Context.MODE_PRIVATE)

    fun save(token: String) {
        prefs.edit().putString(KEY_TOKEN, token).apply()
    }

    fun read(): String? = prefs.getString(KEY_TOKEN, null)

    companion object {
        private const val KEY_TOKEN = "fcm_token"
    }
}
