package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ghost.alpha.domain.model.PerformanceIntelligenceSnapshot
import com.ghost.alpha.domain.usecase.GetPerformanceIntelligenceUseCase
import com.ghost.alpha.utils.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class PerformanceUiState(
    val symbol: String = "AAPL",
    val days: Int = 7,
    val isLoading: Boolean = false,
    val snapshot: PerformanceIntelligenceSnapshot? = null,
    val errorMessage: String? = null
)

@HiltViewModel
class PerformanceViewModel @Inject constructor(
    private val getPerformanceIntelligenceUseCase: GetPerformanceIntelligenceUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(PerformanceUiState())
    val uiState: StateFlow<PerformanceUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun updateSymbol(value: String) {
        _uiState.update { it.copy(symbol = value.uppercase().trim(), errorMessage = null) }
    }

    fun updateDays(value: String) {
        val parsed = value.toIntOrNull()?.coerceIn(1, 30) ?: _uiState.value.days
        _uiState.update { it.copy(days = parsed, errorMessage = null) }
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            runCatching {
                getPerformanceIntelligenceUseCase(
                    days = _uiState.value.days,
                    symbol = _uiState.value.symbol
                )
            }.onSuccess { snapshot ->
                _uiState.update { it.copy(isLoading = false, snapshot = snapshot) }
            }.onFailure { error ->
                _uiState.update { it.copy(isLoading = false, errorMessage = error.toUserMessage()) }
            }
        }
    }
}
