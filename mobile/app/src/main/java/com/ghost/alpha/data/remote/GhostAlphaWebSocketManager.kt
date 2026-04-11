package com.ghost.alpha.data.remote

import com.ghost.alpha.BuildConfig
import com.ghost.alpha.domain.model.RealtimeEvent
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import org.json.JSONObject
import java.time.Instant
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.min

@Singleton
class GhostAlphaWebSocketManager @Inject constructor(
    private val okHttpClient: OkHttpClient
) {
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private val _events = MutableSharedFlow<RealtimeEvent>(extraBufferCapacity = 64)
    val events = _events.asSharedFlow()

    private var webSocket: WebSocket? = null
    private var reconnectAttempts = 0
    private var heartbeatJob: Job? = null
    private var shouldReconnect = true

    fun connect() {
        if (webSocket != null) {
            return
        }
        shouldReconnect = true
        openSocket()
    }

    fun disconnect() {
        shouldReconnect = false
        heartbeatJob?.cancel()
        heartbeatJob = null
        webSocket?.close(1000, "Client requested disconnect")
        webSocket = null
    }

    private fun openSocket() {
        val request = Request.Builder()
            .url(BuildConfig.WS_BASE_URL)
            .build()
        webSocket = okHttpClient.newWebSocket(request, listener)
    }

    private val listener = object : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            reconnectAttempts = 0
            heartbeatJob?.cancel()
            heartbeatJob = scope.launch {
                while (true) {
                    delay(20_000)
                    webSocket.send("{\"type\":\"ping\"}")
                }
            }
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            scope.launch {
                _events.emit(parseEvent(text))
            }
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            this@GhostAlphaWebSocketManager.webSocket = null
            heartbeatJob?.cancel()
            if (shouldReconnect) {
                scheduleReconnect()
            }
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            this@GhostAlphaWebSocketManager.webSocket = null
            heartbeatJob?.cancel()
            scope.launch {
                _events.emit(
                    RealtimeEvent(
                        channel = "system",
                        type = "socket_error",
                        title = "Realtime link unstable",
                        message = t.message ?: "WebSocket failure",
                        severity = "warning",
                        timestamp = Instant.now()
                    )
                )
            }
            if (shouldReconnect) {
                scheduleReconnect()
            }
        }
    }

    private fun scheduleReconnect() {
        reconnectAttempts += 1
        val delayMs = min(30_000L, 1_000L * (1 shl min(reconnectAttempts, 5)))
        scope.launch {
            delay(delayMs)
            if (shouldReconnect && webSocket == null) {
                openSocket()
            }
        }
    }

    private fun parseEvent(raw: String): RealtimeEvent {
        return runCatching {
            val json = JSONObject(raw)
            val payloadJson = json.optJSONObject("payload")
            val payload = buildMap {
                if (payloadJson != null) {
                    payloadJson.keys().forEach { key ->
                        put(key, payloadJson.optString(key))
                    }
                }
            }
            RealtimeEvent(
                channel = json.optString("channel", "unknown"),
                type = json.optString("type", "update"),
                title = json.optString("title", "Ghost Alpha Update"),
                message = json.optString("message", raw),
                severity = json.optString("severity", "info"),
                timestamp = json.optString("timestamp").takeIf { it.isNotBlank() }?.let(Instant::parse)
                    ?: Instant.now(),
                symbol = json.optString("symbol").takeIf { it.isNotBlank() },
                payload = payload
            )
        }.getOrElse {
            RealtimeEvent(
                channel = "unknown",
                type = "update",
                title = "Ghost Alpha Update",
                message = raw,
                severity = "info",
                timestamp = Instant.now()
            )
        }
    }

    fun shutdown() {
        scope.cancel()
    }
}