package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import com.ghost.alpha.domain.model.AgentVote
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
    val errorMessage: String? = null,
    val agreementRatio: Double = 0.0,
    val conflictRatio: Double = 0.0,
    val dominantBias: String = "NEUTRAL"
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
                .onSuccess { signal ->
                    val agreement = computeAgreementRatio(signal.agents)
                    _uiState.update {
                        it.copy(
                            swarmSignal = signal,
                            isLoading = false,
                            agreementRatio = agreement,
                            conflictRatio = 1.0 - agreement,
                            dominantBias = dominantBias(signal.agents)
                        )
                    }
                }
                .onFailure { error -> _uiState.update { it.copy(isLoading = false, errorMessage = error.toUserMessage()) } }
        }
    }

    private fun computeAgreementRatio(votes: List<AgentVote>): Double {
        if (votes.size <= 1) return 1.0
        val normalized = votes.map { it.bias.uppercase() }
        val totalPairs = (normalized.size * (normalized.size - 1)) / 2
        val agreementPairs = normalized.indices.sumOf { i ->
            (i + 1 until normalized.size).count { j -> normalized[i] == normalized[j] }
        }
        return agreementPairs.toDouble() / totalPairs.toDouble()
    }

    private fun dominantBias(votes: List<AgentVote>): String {
        if (votes.isEmpty()) return "NEUTRAL"
        return votes
            .groupingBy { it.bias.uppercase() }
            .eachCount()
            .maxByOrNull { it.value }
            ?.key
            ?: "NEUTRAL"
    }
}