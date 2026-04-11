package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ghost.alpha.domain.model.AutonomousConfig
import com.ghost.alpha.domain.model.AutonomyControlSnapshot
import com.ghost.alpha.domain.usecase.GetAutonomySnapshotUseCase
import com.ghost.alpha.domain.usecase.RunAutonomousOnceUseCase
import com.ghost.alpha.domain.usecase.ToggleTradingUseCase
import com.ghost.alpha.domain.usecase.UpdateAutonomyRiskLimitsUseCase
import com.ghost.alpha.domain.usecase.UpdateAutonomousModeUseCase
import com.ghost.alpha.utils.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AutonomyUiState(
    val isLoading: Boolean = false,
    val isSaving: Boolean = false,
    val snapshot: AutonomyControlSnapshot? = null,
    val symbolFilter: String = "",
    val symbolsInput: String = "AAPL,TSLA,NVDA",
    val intervalSecondsInput: String = "300",
    val dailyLossPctInput: String = "0.05",
    val maxDrawdownPctInput: String = "0.10",
    val errorMessage: String? = null,
    val successMessage: String? = null
)

@HiltViewModel
class AutonomyViewModel @Inject constructor(
    private val getAutonomySnapshotUseCase: GetAutonomySnapshotUseCase,
    private val updateAutonomousModeUseCase: UpdateAutonomousModeUseCase,
    private val runAutonomousOnceUseCase: RunAutonomousOnceUseCase,
    private val toggleTradingUseCase: ToggleTradingUseCase,
    private val updateAutonomyRiskLimitsUseCase: UpdateAutonomyRiskLimitsUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(AutonomyUiState())
    val uiState: StateFlow<AutonomyUiState> = _uiState.asStateFlow()

    init {
        refresh()
    }

    fun updateSymbolFilter(value: String) {
        _uiState.update { it.copy(symbolFilter = value.uppercase().trim()) }
    }

    fun updateSymbolsInput(value: String) {
        _uiState.update { it.copy(symbolsInput = value.uppercase()) }
    }

    fun updateIntervalInput(value: String) {
        _uiState.update { it.copy(intervalSecondsInput = value.filter(Char::isDigit)) }
    }

    fun updateDailyLossInput(value: String) {
        _uiState.update { it.copy(dailyLossPctInput = value.filter { c -> c.isDigit() || c == '.' }) }
    }

    fun updateMaxDrawdownInput(value: String) {
        _uiState.update { it.copy(maxDrawdownPctInput = value.filter { c -> c.isDigit() || c == '.' }) }
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null, successMessage = null) }
            runCatching {
                getAutonomySnapshotUseCase(
                    symbolFilter = _uiState.value.symbolFilter.ifBlank { null }
                )
            }.onSuccess { snapshot ->
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        snapshot = snapshot,
                        intervalSecondsInput = snapshot.controlStatus.autonomous.intervalSeconds.toString(),
                        symbolsInput = snapshot.controlStatus.autonomous.symbols.joinToString(","),
                        dailyLossPctInput = snapshot.controlStatus.dailyLossLimitPct.toString(),
                        maxDrawdownPctInput = snapshot.controlStatus.maxDrawdownLimitPct.toString()
                    )
                }
            }.onFailure { error ->
                _uiState.update { it.copy(isLoading = false, errorMessage = error.toUserMessage()) }
            }
        }
    }

    fun applyAutonomousConfig(enabled: Boolean) {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true, errorMessage = null, successMessage = null) }
            val interval = _uiState.value.intervalSecondsInput.toIntOrNull()?.coerceIn(60, 3600) ?: 300
            val symbols = _uiState.value.symbolsInput
                .split(",")
                .map { it.trim().uppercase() }
                .filter { it.isNotBlank() }
                .distinct()

            runCatching {
                updateAutonomousModeUseCase(
                    AutonomousConfig(
                        enabled = enabled,
                        intervalSeconds = interval,
                        symbols = symbols
                    )
                )
            }.onSuccess {
                _uiState.update { state ->
                    state.copy(isSaving = false, successMessage = if (enabled) "Auto mode enabled" else "Auto mode disabled")
                }
                refresh()
            }.onFailure { error ->
                _uiState.update { it.copy(isSaving = false, errorMessage = error.toUserMessage()) }
            }
        }
    }

    fun runOnce() {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true, errorMessage = null, successMessage = null) }
            runCatching { runAutonomousOnceUseCase() }
                .onSuccess {
                    _uiState.update { it.copy(isSaving = false, successMessage = "Triggered autonomous cycle") }
                    refresh()
                }
                .onFailure { error ->
                    _uiState.update { it.copy(isSaving = false, errorMessage = error.toUserMessage()) }
                }
        }
    }

    fun pauseAiTrading() {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true, errorMessage = null, successMessage = null) }
            runCatching {
                toggleTradingUseCase(false)
                updateAutonomousModeUseCase(
                    AutonomousConfig(
                        enabled = false,
                        intervalSeconds = _uiState.value.intervalSecondsInput.toIntOrNull()?.coerceIn(60, 3600) ?: 300,
                        symbols = _uiState.value.symbolsInput.split(",").map { it.trim().uppercase() }.filter { it.isNotBlank() }
                    )
                )
            }.onSuccess {
                _uiState.update { it.copy(isSaving = false, successMessage = "AI trading paused") }
                refresh()
            }.onFailure { error ->
                _uiState.update { it.copy(isSaving = false, errorMessage = error.toUserMessage()) }
            }
        }
    }

    fun applyRiskLimits() {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true, errorMessage = null, successMessage = null) }
            val daily = _uiState.value.dailyLossPctInput.toDoubleOrNull()?.coerceIn(0.01, 0.5) ?: 0.05
            val drawdown = _uiState.value.maxDrawdownPctInput.toDoubleOrNull()?.coerceIn(0.01, 0.5) ?: 0.10
            runCatching {
                updateAutonomyRiskLimitsUseCase(daily, drawdown)
            }.onSuccess {
                _uiState.update { it.copy(isSaving = false, successMessage = "Risk limits updated") }
                refresh()
            }.onFailure { error ->
                _uiState.update { it.copy(isSaving = false, errorMessage = error.toUserMessage()) }
            }
        }
    }

    fun enableManualOnlyCompliance() {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true, errorMessage = null, successMessage = null) }
            runCatching {
                toggleTradingUseCase(false)
                updateAutonomousModeUseCase(AutonomousConfig(enabled = false, intervalSeconds = 300, symbols = emptyList()))
            }.onSuccess {
                _uiState.update { it.copy(isSaving = false, successMessage = "Manual-only compliance mode enabled") }
                refresh()
            }.onFailure { error ->
                _uiState.update { it.copy(isSaving = false, errorMessage = error.toUserMessage()) }
            }
        }
    }

    fun enableStrictGuardrailCompliance() {
        viewModelScope.launch {
            _uiState.update { it.copy(isSaving = true, errorMessage = null, successMessage = null) }
            runCatching {
                updateAutonomyRiskLimitsUseCase(dailyLossLimitPct = 0.03, maxDrawdownLimitPct = 0.08)
            }.onSuccess {
                _uiState.update { it.copy(isSaving = false, successMessage = "Strict guardrail mode enabled") }
                refresh()
            }.onFailure { error ->
                _uiState.update { it.copy(isSaving = false, errorMessage = error.toUserMessage()) }
            }
        }
    }
}
