package com.ghost.alpha.utils

import android.content.Context
import android.os.Build
import android.provider.Settings
import dagger.hilt.android.qualifiers.ApplicationContext
import java.nio.charset.StandardCharsets
import java.security.MessageDigest
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class DeviceFingerprintProvider @Inject constructor(
    @ApplicationContext private val context: Context
) {
    private val prefs = context.getSharedPreferences("ghost_alpha_device", Context.MODE_PRIVATE)

    fun fingerprint(): String {
        val installId = getOrCreateInstallId()
        val androidId = Settings.Secure.getString(context.contentResolver, Settings.Secure.ANDROID_ID).orEmpty()
        val raw = listOf(
            installId,
            androidId,
            Build.BRAND.orEmpty(),
            Build.MODEL.orEmpty(),
            Build.DEVICE.orEmpty(),
            Build.HARDWARE.orEmpty(),
            Build.VERSION.SDK_INT.toString()
        ).joinToString("|")
        return sha256(raw)
    }

    fun riskSignal(): String {
        val flags = mutableListOf<String>()
        if (Build.FINGERPRINT.contains("generic", ignoreCase = true) ||
            Build.MODEL.contains("Emulator", ignoreCase = true)
        ) {
            flags += "emulator"
        }
        if (Build.TAGS?.contains("test-keys") == true) {
            flags += "test_keys"
        }
        return if (flags.isEmpty()) "normal" else flags.joinToString(",")
    }

    private fun getOrCreateInstallId(): String {
        val existing = prefs.getString(KEY_INSTALL_ID, null)
        if (!existing.isNullOrBlank()) {
            return existing
        }
        val newId = UUID.randomUUID().toString()
        prefs.edit().putString(KEY_INSTALL_ID, newId).apply()
        return newId
    }

    private fun sha256(value: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(value.toByteArray(StandardCharsets.UTF_8))
        return digest.joinToString("") { "%02x".format(it) }
    }

    companion object {
        private const val KEY_INSTALL_ID = "install_id"
    }
}
