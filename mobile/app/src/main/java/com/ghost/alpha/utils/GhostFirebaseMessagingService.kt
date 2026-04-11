package com.ghost.alpha.utils

import android.app.PendingIntent
import android.content.Intent
import android.util.Log
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.ghost.alpha.MainActivity
import com.ghost.alpha.R
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import com.google.firebase.messaging.FirebaseMessaging
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject

@AndroidEntryPoint
class GhostFirebaseMessagingService : FirebaseMessagingService() {
    @Inject
    lateinit var fcmTokenStore: FcmTokenStore

    override fun onCreate() {
        super.onCreate()
        FirebaseMessaging.getInstance().token.addOnSuccessListener { token ->
            fcmTokenStore.save(token)
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val eventType = message.data["event_type"] ?: message.data["type"] ?: "risk_alert"
        val channelId = when (eventType.lowercase()) {
            "trade_execution" -> CHANNEL_TRADE
            "signal_spike" -> CHANNEL_SIGNAL
            else -> CHANNEL_RISK
        }

        val title = message.notification?.title
            ?: message.data["title"]
            ?: when (channelId) {
                CHANNEL_TRADE -> "Trade Execution Update"
                CHANNEL_SIGNAL -> "Signal Spike Detected"
                else -> getString(R.string.app_name)
            }
        val body = message.notification?.body
            ?: message.data["message"]
            ?: "Realtime platform update"

        val launchIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra("notification_channel", channelId)
            putExtra("notification_event_type", eventType)
            putExtra("notification_symbol", message.data["symbol"])
        }
        val pendingIntent = PendingIntent.getActivity(
            this,
            101,
            launchIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )

        val notification = NotificationCompat.Builder(this, channelId)
            .setSmallIcon(android.R.drawable.stat_notify_sync)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        NotificationManagerCompat.from(this).notify((System.currentTimeMillis() % Int.MAX_VALUE).toInt(), notification)
    }

    override fun onNewToken(token: String) {
        fcmTokenStore.save(token)
        // Backend registration endpoint can be wired once exposed server-side.
        Log.i("GhostFCM", "FCM token refreshed")
    }

    companion object {
        const val CHANNEL_TRADE = "ghost_alpha_trade"
        const val CHANNEL_RISK = "ghost_alpha_alerts"
        const val CHANNEL_SIGNAL = "ghost_alpha_signal"
    }
}