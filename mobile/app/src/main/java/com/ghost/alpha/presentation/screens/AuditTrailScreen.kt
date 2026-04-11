package com.ghost.alpha.presentation.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ghost.alpha.presentation.components.ErrorBanner
import com.ghost.alpha.presentation.components.LoadingRow
import com.ghost.alpha.presentation.components.MetricRow
import com.ghost.alpha.presentation.components.SkeletonTerminalCard
import com.ghost.alpha.presentation.components.TerminalCard
import com.ghost.alpha.presentation.viewmodel.AuditTrailViewModel
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Composable
fun AuditTrailScreen(viewModel: AuditTrailViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("Decision Audit Trail", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)

        OutlinedTextField(
            value = state.symbolFilter,
            onValueChange = viewModel::updateSymbolFilter,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Symbol Filter") },
            singleLine = true
        )
        OutlinedTextField(
            value = state.statusFilter,
            onValueChange = viewModel::updateStatusFilter,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Status Filter (ACCEPTED/REJECTED)") },
            singleLine = true
        )

        if (state.isLoadingList) {
            LoadingRow("Loading decision audit summaries...")
        }
        state.errorMessage?.let { ErrorBanner(message = it, onRetry = viewModel::refreshList) }

        TerminalCard(title = "Audit Entries") {
            if (state.entries.isEmpty() && state.isLoadingList) {
                SkeletonTerminalCard(title = "Audit Entries", rows = 4)
            } else if (state.entries.isEmpty()) {
                Text("No audit records found")
            } else {
                LazyColumn(
                    modifier = Modifier
                        .fillMaxWidth()
                        .heightIn(min = 140.dp, max = 280.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(state.entries.take(30)) { entry ->
                        val selected = state.selectedAuditId == entry.auditId
                        Row(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { viewModel.selectAudit(entry.auditId) }
                                .padding(8.dp),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                Text(
                                    "${entry.symbol} • ${entry.decisionType}",
                                    fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium
                                )
                                Text(
                                    formatTs(entry.timestamp.toString()),
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                            Text(
                                entry.status,
                                color = if (entry.status.uppercase() == "ACCEPTED") MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                                fontWeight = FontWeight.SemiBold
                            )
                        }
                    }
                }
            }
        }

        TerminalCard(title = "Decision Replay") {
            if (state.isLoadingReplay) {
                LoadingRow("Reconstructing decision lineage...")
            }
            val replay = state.replay
            if (replay == null) {
                Text("Select an audit entry to replay")
            } else {
                MetricRow("Audit ID", replay.auditId.take(12) + "...")
                MetricRow("Symbol", replay.symbol)
                MetricRow("Type", replay.decisionType)
                MetricRow("Status", replay.status)
                Text("Replay Steps", fontWeight = FontWeight.SemiBold)
                replay.replaySteps.forEach { step ->
                    TerminalCard(title = step.title) {
                        Text(step.summary)
                        val compact = step.payload.entries.take(5).joinToString(" | ") { "${it.key}=${it.value}" }
                        if (compact.isNotBlank()) {
                            Text(compact, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
                if (replay.whyNot.isNotEmpty()) {
                    Text("Why Not", fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.error)
                    replay.whyNot.forEach { line ->
                        Text("• $line", color = MaterialTheme.colorScheme.error)
                    }
                }
            }
        }
    }
}

private fun formatTs(raw: String): String {
    return runCatching {
        DateTimeFormatter.ofPattern("HH:mm:ss")
            .withZone(ZoneId.systemDefault())
            .format(java.time.Instant.parse(raw))
    }.getOrDefault(raw)
}
