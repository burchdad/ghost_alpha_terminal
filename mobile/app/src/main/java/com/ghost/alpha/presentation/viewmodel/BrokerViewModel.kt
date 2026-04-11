package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ghost.alpha.domain.model.Broker
import com.ghost.alpha.domain.usecase.ConnectBrokerUseCase
import com.ghost.alpha.domain.usecase.DisconnectBrokerUseCase
import com.ghost.alpha.domain.usecase.FetchBrokersUseCase
import com.ghost.alpha.utils.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class BrokerUiState(
    val brokers: List<Broker> = emptyList(),
    val pendingConnectUrl: String? = null,
    val callbackState: String? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

@HiltViewModel
class BrokerViewModel @Inject constructor(
    private val fetchBrokersUseCase: FetchBrokersUseCase,
    private val connectBrokerUseCase: ConnectBrokerUseCase,
    private val disconnectBrokerUseCase: DisconnectBrokerUseCase
) : ViewModel() {
    private val _uiState = MutableStateFlow(BrokerUiState())
    val uiState: StateFlow<BrokerUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            runCatching { fetchBrokersUseCase() }
                .onSuccess { brokers -> _uiState.update { it.copy(brokers = brokers, isLoading = false) } }
                .onFailure { error -> _uiState.update { it.copy(isLoading = false, errorMessage = error.toUserMessage()) } }
        }
    }

    fun prepareConnect(provider: String) {
        _uiState.update { it.copy(pendingConnectUrl = connectBrokerUseCase(provider)) }
    }

    fun onCallback(url: String?) {
        if (url.isNullOrBlank()) {
            return
        }
        _uiState.update { it.copy(callbackState = url, pendingConnectUrl = null) }
        refresh()
    }

    fun disconnect(provider: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            runCatching { disconnectBrokerUseCase(provider) }
                .onSuccess { refresh() }
                .onFailure { error -> _uiState.update { it.copy(isLoading = false, errorMessage = error.toUserMessage()) } }
        }
    }
}