package com.ghost.alpha

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import android.util.Log
import com.ghost.alpha.utils.GhostFirebaseMessagingService
import com.google.firebase.FirebaseApp
import com.google.firebase.messaging.FirebaseMessaging
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class GhostAlphaApp : Application() {
    companion object {
        private const val TAG = "GhostAlphaApp"
    }

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
        val firebaseApp = FirebaseApp.initializeApp(this)
        if (firebaseApp == null) {
            Log.w(TAG, "Firebase not configured; skipping FCM token initialization")
            return
        }

        FirebaseMessaging.getInstance().token.addOnSuccessListener { token ->
            getSharedPreferences("ghost_alpha_fcm", MODE_PRIVATE)
                .edit()
                .putString("fcm_token", token)
                .apply()
        }.addOnFailureListener { error ->
            Log.w(TAG, "Failed to fetch FCM token", error)
        }
    }
}