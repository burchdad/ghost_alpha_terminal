package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ghost.alpha.domain.model.ExecutionStatus
import com.ghost.alpha.domain.model.RiskSeverity
import com.ghost.alpha.domain.model.TradeExecutionAudit
import com.ghost.alpha.domain.model.TradeGuardrail
import com.ghost.alpha.domain.usecase.ApproveTradeWithGuardrailsUseCase
import com.ghost.alpha.domain.usecase.AssessTradeRisksUseCase
import com.ghost.alpha.domain.usecase.GetRecentTradeAuditsUseCase
import com.ghost.alpha.domain.usecase.GetTradeAuditUseCase
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class TradeGuardrailsViewModel @Inject constructor(
    private val assessTradeRisksUseCase: AssessTradeRisksUseCase,
    private val approveTradeWithGuardrailsUseCase: ApproveTradeWithGuardrailsUseCase,
    private val getTradeAuditUseCase: GetTradeAuditUseCase,
    private val getRecentTradeAuditsUseCase: GetRecentTradeAuditsUseCase
) : ViewModel() {

    private val _assessmentState = MutableStateFlow<GuardrailAssessmentState>(GuardrailAssessmentState.Idle)
    val assessmentState: StateFlow<GuardrailAssessmentState> = _assessmentState.asStateFlow()

    private val _approvalState = MutableStateFlow<GuardrailApprovalState>(GuardrailApprovalState.Idle)
    val approvalState: StateFlow<GuardrailApprovalState> = _approvalState.asStateFlow()

    private val _auditState = MutableStateFlow<TradeAuditState>(TradeAuditState.Idle)
    val auditState: StateFlow<TradeAuditState> = _auditState.asStateFlow()

    private val _recentAuditsState = MutableStateFlow<RecentAuditsState>(RecentAuditsState.Idle)
    val recentAuditsState: StateFlow<RecentAuditsState> = _recentAuditsState.asStateFlow()

    // Current trade being assessed
    private val _currentTradeId = MutableStateFlow<String?>(null)
    val currentTradeId: StateFlow<String?> = _currentTradeId.asStateFlow()

    fun assessTradeRisk(symbol: String, quantity: Double, side: String, price: Double) {
        viewModelScope.launch {
            _assessmentState.value = GuardrailAssessmentState.Loading
            try {
                val result = assessTradeRisksUseCase(symbol, quantity, side, price)
                result.onSuccess { guardrail ->
                    _currentTradeId.value = guardrail.tradeId
                    _assessmentState.value = GuardrailAssessmentState.Success(guardrail)
                }.onFailure { error ->
                    _assessmentState.value = GuardrailAssessmentState.Error(error.message ?: "Unknown error")
                }
            } catch (e: Exception) {
                _assessmentState.value = GuardrailAssessmentState.Error(e.message ?: "Unknown error")
            }
        }
    }

    fun approveTradeWithGuardrails(tradeId: String, approved: Boolean, reason: String = "", userOverride: Boolean = false) {
        viewModelScope.launch {
            _approvalState.value = GuardrailApprovalState.Loading
            try {
                val result = approveTradeWithGuardrailsUseCase(tradeId, approved, reason, userOverride)
                result.onSuccess { audit ->
                    _approvalState.value = GuardrailApprovalState.Success(audit)
                }.onFailure { error ->
                    _approvalState.value = GuardrailApprovalState.Error(error.message ?: "Unknown error")
                }
            } catch (e: Exception) {
                _approvalState.value = GuardrailApprovalState.Error(e.message ?: "Unknown error")
            }
        }
    }

    fun getTradeAudit(tradeId: String) {
        viewModelScope.launch {
            _auditState.value = TradeAuditState.Loading
            try {
                val result = getTradeAuditUseCase(tradeId)
                result.onSuccess { audit ->
                    _auditState.value = TradeAuditState.Success(audit)
                }.onFailure { error ->
                    _auditState.value = TradeAuditState.Error(error.message ?: "Unknown error")
                }
            } catch (e: Exception) {
                _auditState.value = TradeAuditState.Error(e.message ?: "Unknown error")
            }
        }
    }

    fun getRecentTradeAudits(limit: Int = 10) {
        viewModelScope.launch {
            _recentAuditsState.value = RecentAuditsState.Loading
            try {
                val result = getRecentTradeAuditsUseCase(limit)
                result.onSuccess { audits ->
                    _recentAuditsState.value = RecentAuditsState.Success(audits)
                }.onFailure { error ->
                    _recentAuditsState.value = RecentAuditsState.Error(error.message ?: "Unknown error")
                }
            } catch (e: Exception) {
                _recentAuditsState.value = RecentAuditsState.Error(e.message ?: "Unknown error")
            }
        }
    }

    fun clearCurrentTrade() {
        _currentTradeId.value = null
        _assessmentState.value = GuardrailAssessmentState.Idle
    }

    fun clearApprovalState() {
        _approvalState.value = GuardrailApprovalState.Idle
    }
}

sealed class GuardrailAssessmentState {
    data object Idle : GuardrailAssessmentState()
    data object Loading : GuardrailAssessmentState()
    data class Success(val guardrail: TradeGuardrail) : GuardrailAssessmentState()
    data class Error(val message: String) : GuardrailAssessmentState()
}

sealed class GuardrailApprovalState {
    data object Idle : GuardrailApprovalState()
    data object Loading : GuardrailApprovalState()
    data class Success(val audit: TradeExecutionAudit) : GuardrailApprovalState()
    data class Error(val message: String) : GuardrailApprovalState()
}

sealed class TradeAuditState {
    data object Idle : TradeAuditState()
    data object Loading : TradeAuditState()
    data class Success(val audit: TradeExecutionAudit) : TradeAuditState()
    data class Error(val message: String) : TradeAuditState()
}

sealed class RecentAuditsState {
    data object Idle : RecentAuditsState()
    data object Loading : RecentAuditsState()
    data class Success(val audits: List<TradeExecutionAudit>) : RecentAuditsState()
    data class Error(val message: String) : RecentAuditsState()
}
