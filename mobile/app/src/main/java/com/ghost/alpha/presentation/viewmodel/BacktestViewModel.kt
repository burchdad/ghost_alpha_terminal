package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ghost.alpha.domain.model.BacktestRequest
import com.ghost.alpha.domain.model.BacktestResult
import com.ghost.alpha.domain.usecase.RunBacktestUseCase
import com.ghost.alpha.utils.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.temporal.ChronoUnit

data class BacktestUiState(
    val symbol: String = "AAPL",
    val timeframe: String = "1d",
    val result: BacktestResult? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

@HiltViewModel
class BacktestViewModel @Inject constructor(
    private val runBacktestUseCase: RunBacktestUseCase
) : ViewModel() {
    private val _uiState = MutableStateFlow(BacktestUiState())
    val uiState: StateFlow<BacktestUiState> = _uiState.asStateFlow()

    fun updateSymbol(value: String) {
        _uiState.update { it.copy(symbol = value.uppercase(), errorMessage = null) }
    }

    fun runBacktest() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            runCatching {
                runBacktestUseCase(
                    BacktestRequest(
                        symbol = _uiState.value.symbol,
                        timeframe = _uiState.value.timeframe,
                        startDate = Instant.now().minus(90, ChronoUnit.DAYS),
                        endDate = Instant.now(),
                        initialCapital = 100000.0,
                        riskPerTrade = 0.01,
                        takeProfitPct = 0.03,
                        stopLossPct = 0.02,
                        maxHoldPeriods = 5,
                        enableEvolution = true,
                        enableCompounding = true
                    )
                )
            }.onSuccess { result ->
                _uiState.update { it.copy(result = result, isLoading = false) }
            }.onFailure { error ->
                _uiState.update { it.copy(isLoading = false, errorMessage = error.toUserMessage()) }
            }
        }
    }
}