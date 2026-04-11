package com.ghost.alpha.presentation.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ghost.alpha.presentation.components.ErrorBanner
import com.ghost.alpha.presentation.components.LoadingRow
import com.ghost.alpha.presentation.components.TerminalCard
import com.ghost.alpha.presentation.viewmodel.CopilotViewModel

@Composable
fun CopilotCommandScreen(viewModel: CopilotViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text("Ghost Copilot", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
        Text("Mode: ${state.mode.ifBlank { "unassigned" }}", style = MaterialTheme.typography.labelMedium)

        if (state.isLoadingContext) {
            LoadingRow("Loading command context...")
        }

        if (state.greeting.isNotBlank()) {
            TerminalCard(title = "Context") {
                Text(state.greeting)
                state.telemetrySummary?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall)
                }
            }
        }

        state.errorMessage?.let {
            ErrorBanner(message = it, onRetry = viewModel::loadContext)
        }

        TerminalCard(title = "Command Console") {
            LazyColumn(
                modifier = Modifier
                    .fillMaxWidth()
                    .heightIn(min = 220.dp, max = 360.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                items(state.messages) { message ->
                    val isUser = message.role.equals("user", ignoreCase = true)
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
                    ) {
                        Text(
                            text = message.text,
                            modifier = Modifier
                                .fillMaxWidth(0.85f)
                                .background(
                                    color = if (isUser) MaterialTheme.colorScheme.primary.copy(alpha = 0.16f)
                                    else MaterialTheme.colorScheme.surfaceVariant,
                                    shape = RoundedCornerShape(12.dp)
                                )
                                .padding(10.dp)
                        )
                    }
                }
            }
        }

        if (state.requiresConfirmation) {
            TerminalCard(title = "Action Confirmation") {
                Text(state.confirmationPrompt ?: "This action requires explicit confirmation.")
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(10.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Button(
                        onClick = viewModel::confirmPendingAction,
                        modifier = Modifier.weight(1f),
                        enabled = !state.isSending
                    ) {
                        Text("Confirm")
                    }
                    Button(
                        onClick = viewModel::dismissPendingAction,
                        modifier = Modifier.weight(1f),
                        enabled = !state.isSending
                    ) {
                        Text("Cancel")
                    }
                }
            }
        }

        OutlinedTextField(
            value = state.draft,
            onValueChange = viewModel::updateDraft,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Ask Ghost Copilot") },
            placeholder = { Text("Run a quick risk check for TSLA") },
            minLines = 2,
            maxLines = 4,
            enabled = !state.isSending
        )

        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Button(
                onClick = viewModel::sendMessage,
                modifier = Modifier.weight(1f),
                enabled = !state.isSending
            ) {
                Text(if (state.isSending) "Sending..." else "Send Command")
            }
            Button(
                onClick = {
                    if (!state.isSending) viewModel.updateDraft("Run a quick risk check for AAPL")
                },
                modifier = Modifier.weight(1f),
                enabled = !state.isSending
            ) {
                Text("Quick Risk")
            }
        }
    }
}
