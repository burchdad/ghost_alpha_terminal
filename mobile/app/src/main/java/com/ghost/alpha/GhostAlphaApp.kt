package com.ghost.alpha

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.ghost.alpha.utils.GhostFirebaseMessagingService
import com.google.firebase.messaging.FirebaseMessaging
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class GhostAlphaApp : Application() {
    override fun onCreate() {
        super.onCreate()
        createNotificationChannel()
        initializeFirebaseToken()
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return
        }

        val manager = getSystemService(NotificationManager::class.java)
        val channels = listOf(
            NotificationChannel(
                GhostFirebaseMessagingService.CHANNEL_RISK,
                "Risk Alerts",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Critical risk, policy, and security alerts"
            },
            NotificationChannel(
                GhostFirebaseMessagingService.CHANNEL_TRADE,
                "Trade Execution",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Order execution and fill status updates"
            },
            NotificationChannel(
                GhostFirebaseMessagingService.CHANNEL_SIGNAL,
                "Signal Spikes",
                NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "High-confidence AI signal spike updates"
            }
        )

        manager.createNotificationChannels(channels)
    }

    private fun initializeFirebaseToken() {
        FirebaseMessaging.getInstance().token.addOnSuccessListener { token ->
            getSharedPreferences("ghost_alpha_fcm", MODE_PRIVATE)
                .edit()
                .putString("fcm_token", token)
                .apply()
        }
    }
}