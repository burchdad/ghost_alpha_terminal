package com.ghost.alpha.domain.repository

import com.ghost.alpha.domain.model.RealtimeEvent
import kotlinx.coroutines.flow.SharedFlow

interface RealtimeRepository {
    val events: SharedFlow<RealtimeEvent>
    fun connect()
    fun disconnect()
}