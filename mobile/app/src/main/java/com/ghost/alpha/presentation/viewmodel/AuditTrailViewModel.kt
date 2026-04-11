package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ghost.alpha.domain.model.DecisionAuditDetail
import com.ghost.alpha.domain.model.DecisionAuditSummary
import com.ghost.alpha.domain.model.DecisionReplay
import com.ghost.alpha.domain.usecase.GetDecisionAuditDetailUseCase
import com.ghost.alpha.domain.usecase.GetDecisionReplayUseCase
import com.ghost.alpha.domain.usecase.ListDecisionAuditsUseCase
import com.ghost.alpha.utils.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AuditTrailUiState(
    val isLoadingList: Boolean = false,
    val isLoadingReplay: Boolean = false,
    val entries: List<DecisionAuditSummary> = emptyList(),
    val selectedAuditId: String? = null,
    val replay: DecisionReplay? = null,
    val detail: DecisionAuditDetail? = null,
    val symbolFilter: String = "",
    val statusFilter: String = "",
    val errorMessage: String? = null
)

@HiltViewModel
class AuditTrailViewModel @Inject constructor(
    private val listDecisionAuditsUseCase: ListDecisionAuditsUseCase,
    private val getDecisionReplayUseCase: GetDecisionReplayUseCase,
    private val getDecisionAuditDetailUseCase: GetDecisionAuditDetailUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(AuditTrailUiState())
    val uiState: StateFlow<AuditTrailUiState> = _uiState.asStateFlow()

    init {
        refreshList()
    }

    fun updateSymbolFilter(value: String) {
        _uiState.update { it.copy(symbolFilter = value.uppercase().trim(), errorMessage = null) }
    }

    fun updateStatusFilter(value: String) {
        _uiState.update { it.copy(statusFilter = value.uppercase().trim(), errorMessage = null) }
    }

    fun refreshList() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoadingList = true, errorMessage = null) }
            runCatching {
                listDecisionAuditsUseCase(
                    limit = 80,
                    symbol = _uiState.value.symbolFilter.ifBlank { null },
                    status = _uiState.value.statusFilter.ifBlank { null }
                )
            }.onSuccess { items ->
                val selected = _uiState.value.selectedAuditId
                val nextSelected = selected?.takeIf { id -> items.any { it.auditId == id } } ?: items.firstOrNull()?.auditId
                _uiState.update {
                    it.copy(
                        isLoadingList = false,
                        entries = items,
                        selectedAuditId = nextSelected,
                        errorMessage = null
                    )
                }
                nextSelected?.let { loadReplay(it) }
            }.onFailure { error ->
                _uiState.update { it.copy(isLoadingList = false, errorMessage = error.toUserMessage()) }
            }
        }
    }

    fun selectAudit(auditId: String) {
        _uiState.update { it.copy(selectedAuditId = auditId, errorMessage = null) }
        loadReplay(auditId)
    }

    private fun loadReplay(auditId: String) {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoadingReplay = true, errorMessage = null) }
            val replayResult = runCatching { getDecisionReplayUseCase(auditId) }
            val detailResult = runCatching { getDecisionAuditDetailUseCase(auditId) }

            if (replayResult.isSuccess && detailResult.isSuccess) {
                _uiState.update {
                    it.copy(
                        isLoadingReplay = false,
                        replay = replayResult.getOrNull(),
                        detail = detailResult.getOrNull(),
                        errorMessage = null
                    )
                }
            } else {
                _uiState.update {
                    it.copy(
                        isLoadingReplay = false,
                        errorMessage = replayResult.exceptionOrNull()?.toUserMessage()
                            ?: detailResult.exceptionOrNull()?.toUserMessage()
                            ?: "Failed to load decision replay"
                    )
                }
            }
        }
    }
}
