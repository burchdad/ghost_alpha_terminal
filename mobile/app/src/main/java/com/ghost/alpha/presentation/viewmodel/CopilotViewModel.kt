package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ghost.alpha.domain.model.CopilotMessage
import com.ghost.alpha.domain.usecase.GetCopilotContextUseCase
import com.ghost.alpha.domain.usecase.GetCopilotTelemetrySummaryUseCase
import com.ghost.alpha.domain.usecase.SendCopilotMessageUseCase
import com.ghost.alpha.utils.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import java.time.Instant
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class CopilotUiState(
    val isLoadingContext: Boolean = false,
    val isSending: Boolean = false,
    val greeting: String = "",
    val mode: String = "",
    val messages: List<CopilotMessage> = emptyList(),
    val draft: String = "",
    val errorMessage: String? = null,
    val requiresConfirmation: Boolean = false,
    val confirmationPrompt: String? = null,
    val pendingAction: Map<String, String>? = null,
    val telemetrySummary: String? = null
)

@HiltViewModel
class CopilotViewModel @Inject constructor(
    private val getCopilotContextUseCase: GetCopilotContextUseCase,
    private val sendCopilotMessageUseCase: SendCopilotMessageUseCase,
    private val getCopilotTelemetrySummaryUseCase: GetCopilotTelemetrySummaryUseCase
) : ViewModel() {

    private val _uiState = MutableStateFlow(CopilotUiState())
    val uiState: StateFlow<CopilotUiState> = _uiState.asStateFlow()

    init {
        loadContext()
    }

    fun updateDraft(value: String) {
        _uiState.update { it.copy(draft = value, errorMessage = null) }
    }

    fun loadContext() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoadingContext = true, errorMessage = null) }
            runCatching { getCopilotContextUseCase() }
                .onSuccess { context ->
                    _uiState.update {
                        it.copy(
                            isLoadingContext = false,
                            greeting = context.greeting,
                            mode = context.mode,
                            messages = context.history
                        )
                    }
                    loadTelemetrySummary()
                }
                .onFailure { error ->
                    _uiState.update { it.copy(isLoadingContext = false, errorMessage = error.toUserMessage()) }
                }
        }
    }

    fun sendMessage() {
        val message = _uiState.value.draft.trim()
        if (message.isEmpty() || _uiState.value.isSending) return

        viewModelScope.launch {
            val userMsg = CopilotMessage(
                role = "user",
                text = message,
                timestamp = Instant.now()
            )
            _uiState.update {
                it.copy(
                    isSending = true,
                    draft = "",
                    errorMessage = null,
                    messages = it.messages + userMsg
                )
            }

            runCatching {
                sendCopilotMessageUseCase(
                    message = message,
                    confirm = false,
                    pendingAction = null
                )
            }.onSuccess { result ->
                _uiState.update {
                    it.copy(
                        isSending = false,
                        mode = result.mode,
                        messages = it.messages + CopilotMessage(
                            role = "assistant",
                            text = result.reply,
                            timestamp = Instant.now()
                        ),
                        requiresConfirmation = result.requiresConfirmation,
                        confirmationPrompt = result.confirmationPrompt,
                        pendingAction = result.pendingAction,
                        errorMessage = null
                    )
                }
            }.onFailure { error ->
                _uiState.update { it.copy(isSending = false, errorMessage = error.toUserMessage()) }
            }
        }
    }

    fun confirmPendingAction() {
        val action = _uiState.value.pendingAction ?: return
        viewModelScope.launch {
            _uiState.update { it.copy(isSending = true, errorMessage = null) }
            runCatching {
                sendCopilotMessageUseCase(
                    message = "Confirm action",
                    confirm = true,
                    pendingAction = action
                )
            }.onSuccess { result ->
                _uiState.update {
                    it.copy(
                        isSending = false,
                        requiresConfirmation = false,
                        confirmationPrompt = null,
                        pendingAction = null,
                        messages = it.messages + CopilotMessage(
                            role = "assistant",
                            text = result.reply,
                            timestamp = Instant.now()
                        ),
                        mode = result.mode
                    )
                }
            }.onFailure { error ->
                _uiState.update { it.copy(isSending = false, errorMessage = error.toUserMessage()) }
            }
        }
    }

    fun dismissPendingAction() {
        _uiState.update {
            it.copy(
                requiresConfirmation = false,
                confirmationPrompt = null,
                pendingAction = null
            )
        }
    }

    private fun loadTelemetrySummary() {
        viewModelScope.launch {
            runCatching { getCopilotTelemetrySummaryUseCase() }
                .onSuccess { summary ->
                    _uiState.update {
                        it.copy(
                            telemetrySummary = "Events ${summary.totalEvents} | Success ${(summary.successRate * 100).toInt()}% | Confirm ${(summary.confirmationRate * 100).toInt()}%"
                        )
                    }
                }
                .onFailure {
                    // Non-blocking for command flow.
                }
        }
    }
}
