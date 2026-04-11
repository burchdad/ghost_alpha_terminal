package com.ghost.alpha.data.repository

import com.ghost.alpha.data.remote.GhostAlphaWebSocketManager
import com.ghost.alpha.domain.model.RealtimeEvent
import com.ghost.alpha.domain.repository.RealtimeRepository
import kotlinx.coroutines.flow.SharedFlow
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class RealtimeRepositoryImpl @Inject constructor(
    private val webSocketManager: GhostAlphaWebSocketManager
) : RealtimeRepository {
    override val events: SharedFlow<RealtimeEvent> = webSocketManager.events

    override fun connect() {
        webSocketManager.connect()
    }

    override fun disconnect() {
        webSocketManager.disconnect()
    }
}