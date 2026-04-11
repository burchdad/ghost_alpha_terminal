package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ghost.alpha.domain.model.TradeExecutionRequest
import com.ghost.alpha.domain.model.TradeExecutionResult
import com.ghost.alpha.domain.usecase.ExecuteTradeUseCase
import com.ghost.alpha.domain.usecase.FetchSignalsUseCase
import com.ghost.alpha.utils.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class TradingUiState(
    val symbol: String = "AAPL",
    val strategy: String = "swarm_consensus",
    val side: String = "LONG",
    val entryPrice: String = "195.00",
    val confidence: String = "0.67",
    val latestSignal: String? = null,
    val latestConfidence: Double? = null,
    val result: TradeExecutionResult? = null,
    val isLoading: Boolean = false,
    val errorMessage: String? = null
)

@HiltViewModel
class TradingViewModel @Inject constructor(
    private val executeTradeUseCase: ExecuteTradeUseCase,
    private val fetchSignalsUseCase: FetchSignalsUseCase
) : ViewModel() {
    private val _uiState = MutableStateFlow(TradingUiState())
    val uiState: StateFlow<TradingUiState> = _uiState.asStateFlow()

    init {
        loadSignal()
    }

    fun updateSymbol(value: String) {
        _uiState.update { it.copy(symbol = value.uppercase(), errorMessage = null) }
    }

    fun updateStrategy(value: String) {
        _uiState.update { it.copy(strategy = value, errorMessage = null) }
    }

    fun updateSide(value: String) {
        _uiState.update { it.copy(side = value, errorMessage = null) }
    }

    fun updateEntryPrice(value: String) {
        _uiState.update { it.copy(entryPrice = value, errorMessage = null) }
    }

    fun updateConfidence(value: String) {
        _uiState.update { it.copy(confidence = value, errorMessage = null) }
    }

    fun loadSignal() {
        viewModelScope.launch {
            runCatching { fetchSignalsUseCase(_uiState.value.symbol) }
                .onSuccess { signal ->
                    _uiState.update {
                        it.copy(
                            latestSignal = signal.signal,
                            latestConfidence = signal.confidence,
                            confidence = signal.confidence.toString()
                        )
                    }
                }
        }
    }

    fun executeTrade() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            val price = _uiState.value.entryPrice.toDoubleOrNull()
            val confidence = _uiState.value.confidence.toDoubleOrNull()
            if (price == null || confidence == null) {
                _uiState.update { it.copy(isLoading = false, errorMessage = "Enter a valid price and confidence") }
                return@launch
            }

            runCatching {
                executeTradeUseCase(
                    TradeExecutionRequest(
                        symbol = _uiState.value.symbol,
                        strategy = _uiState.value.strategy,
                        side = _uiState.value.side,
                        entryPrice = price,
                        stopLossPct = 0.02,
                        takeProfitPct = 0.03,
                        accountBalance = 100000.0,
                        riskPerTrade = 0.01,
                        confidence = confidence
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