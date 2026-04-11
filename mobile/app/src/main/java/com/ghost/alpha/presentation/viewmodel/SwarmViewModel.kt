package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ghost.alpha.domain.model.SwarmSignal
import com.ghost.alpha.domain.usecase.FetchSwarmSignalsUseCase
import com.ghost.alpha.utils.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SwarmUiState(
    val symbol: String = "AAPL",
    val swarmSignal: SwarmSignal? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

@HiltViewModel
class SwarmViewModel @Inject constructor(
    private val fetchSwarmSignalsUseCase: FetchSwarmSignalsUseCase
) : ViewModel() {
    private val _uiState = MutableStateFlow(SwarmUiState())
    val uiState: StateFlow<SwarmUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun updateSymbol(value: String) {
        _uiState.update { it.copy(symbol = value.uppercase(), errorMessage = null) }
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            runCatching { fetchSwarmSignalsUseCase(_uiState.value.symbol) }
                .onSuccess { signal -> _uiState.update { it.copy(swarmSignal = signal, isLoading = false) } }
                .onFailure { error -> _uiState.update { it.copy(isLoading = false, errorMessage = error.toUserMessage()) } }
        }
    }
}