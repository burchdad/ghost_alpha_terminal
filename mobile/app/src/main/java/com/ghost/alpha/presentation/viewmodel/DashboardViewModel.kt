package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ghost.alpha.domain.model.AlertItem
import com.ghost.alpha.domain.model.PortfolioSnapshot
import com.ghost.alpha.domain.model.Signal
import com.ghost.alpha.domain.model.SwarmSignal
import com.ghost.alpha.domain.repository.RealtimeRepository
import com.ghost.alpha.domain.usecase.FetchPortfolioUseCase
import com.ghost.alpha.domain.usecase.FetchSignalsUseCase
import com.ghost.alpha.domain.usecase.FetchSwarmSignalsUseCase
import com.ghost.alpha.utils.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.Instant
import java.util.UUID

data class DashboardUiState(
    val symbol: String = "AAPL",
    val portfolio: PortfolioSnapshot? = null,
    val featuredSignal: Signal? = null,
    val featuredSwarm: SwarmSignal? = null,
    val alerts: List<AlertItem> = emptyList(),
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val fetchPortfolioUseCase: FetchPortfolioUseCase,
    private val fetchSignalsUseCase: FetchSignalsUseCase,
    private val fetchSwarmSignalsUseCase: FetchSwarmSignalsUseCase,
    private val realtimeRepository: RealtimeRepository
) : ViewModel() {
    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    init {
        realtimeRepository.connect()
        observeRealtime()
        refresh()
    }

    fun refresh(symbol: String = _uiState.value.symbol) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null, symbol = symbol.uppercase()) }
            runCatching {
                Triple(
                    fetchPortfolioUseCase(),
                    fetchSignalsUseCase(symbol.uppercase()),
                    fetchSwarmSignalsUseCase(symbol.uppercase())
                )
            }.onSuccess { (portfolio, signal, swarm) ->
                _uiState.update {
                    it.copy(
                        portfolio = portfolio,
                        featuredSignal = signal,
                        featuredSwarm = swarm,
                        isLoading = false
                    )
                }
            }.onFailure { error ->
                _uiState.update { it.copy(isLoading = false, errorMessage = error.toUserMessage()) }
            }
        }
    }

    private fun observeRealtime() {
        viewModelScope.launch {
            realtimeRepository.events.collect { event ->
                _uiState.update { state ->
                    state.copy(
                        alerts = listOf(
                            AlertItem(
                                id = UUID.randomUUID().toString(),
                                title = event.title,
                                message = event.message,
                                severity = event.severity,
                                timestamp = event.timestamp,
                                symbol = event.symbol
                            )
                        ) + state.alerts.take(5)
                    )
                }
            }
        }

        _uiState.update {
            it.copy(
                alerts = listOf(
                    AlertItem(
                        id = UUID.randomUUID().toString(),
                        title = "Realtime layer armed",
                        message = "WebSocket manager is ready and waiting for live backend events.",
                        severity = "info",
                        timestamp = Instant.now()
                    )
                )
            )
        }
    }

    override fun onCleared() {
        realtimeRepository.disconnect()
        super.onCleared()
    }
}