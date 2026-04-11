package com.ghost.alpha.presentation.screens

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
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ghost.alpha.presentation.components.ErrorBanner
import com.ghost.alpha.presentation.components.LoadingRow
import com.ghost.alpha.presentation.components.MetricRow
import com.ghost.alpha.presentation.components.TerminalCard
import com.ghost.alpha.presentation.viewmodel.AutonomyViewModel

@Composable
fun AutonomyControlCenterScreen(viewModel: AutonomyViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("Autonomy Control Center", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)

        if (state.isLoading) {
            LoadingRow("Syncing autonomy status...")
        }

        state.errorMessage?.let { ErrorBanner(message = it, onRetry = viewModel::refresh) }
        state.successMessage?.let { msg ->
            Text(msg, color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodyMedium)
        }

        val snapshot = state.snapshot
        if (snapshot != null) {
            TerminalCard(title = "Engine Status") {
                MetricRow("System", snapshot.controlStatus.systemStatus)
                MetricRow("Trading Enabled", snapshot.controlStatus.tradingEnabled.toString())
                MetricRow("Auto Mode", snapshot.controlStatus.autonomous.enabled.toString())
                MetricRow("Interval", "${snapshot.controlStatus.autonomous.intervalSeconds}s")
                MetricRow("Cycles Run", snapshot.controlStatus.autonomous.cyclesRun.toString())
                snapshot.controlStatus.autonomous.lastError?.let { MetricRow("Last Error", it) }
                MetricRow("Daily PnL", String.format("%.2f", snapshot.controlStatus.dailyPnl))
                MetricRow("Daily Loss Limit %", String.format("%.2f", snapshot.controlStatus.dailyLossLimitPct * 100) + "%")
                MetricRow("Max Drawdown %", String.format("%.2f", snapshot.controlStatus.maxDrawdownLimitPct * 100) + "%")
            }

            TerminalCard(title = "Autonomy Configuration") {
                OutlinedTextField(
                    value = state.intervalSecondsInput,
                    onValueChange = viewModel::updateIntervalInput,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Interval Seconds (60-3600)") },
                    singleLine = true
                )
                OutlinedTextField(
                    value = state.symbolsInput,
                    onValueChange = viewModel::updateSymbolsInput,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Allowed Symbols (comma-separated)") },
                    singleLine = true
                )
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = { viewModel.applyAutonomousConfig(true) },
                        enabled = !state.isSaving,
                        modifier = Modifier.weight(1f)
                    ) { Text("Enable Auto") }
                    Button(
                        onClick = { viewModel.applyAutonomousConfig(false) },
                        enabled = !state.isSaving,
                        modifier = Modifier.weight(1f)
                    ) { Text("Disable Auto") }
                }
                Button(
                    onClick = viewModel::runOnce,
                    enabled = !state.isSaving,
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text("Run Autonomous Once")
                }
            }

            TerminalCard(title = "Guardrails + Kill Switch") {
                OutlinedTextField(
                    value = state.dailyLossPctInput,
                    onValueChange = viewModel::updateDailyLossInput,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Daily Loss Limit Pct (0.01-0.50)") },
                    singleLine = true
                )
                OutlinedTextField(
                    value = state.maxDrawdownPctInput,
                    onValueChange = viewModel::updateMaxDrawdownInput,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Max Drawdown Pct (0.01-0.50)") },
                    singleLine = true
                )
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = viewModel::applyRiskLimits,
                        enabled = !state.isSaving,
                        modifier = Modifier.weight(1f)
                    ) { Text("Apply Limits") }
                    Button(
                        onClick = viewModel::pauseAiTrading,
                        enabled = !state.isSaving,
                        modifier = Modifier.weight(1f)
                    ) { Text("Pause AI Trading") }
                }
            }

            TerminalCard(title = "Compliance Mode") {
                MetricRow("Manual-only", snapshot.complianceMode.manualOnly.toString())
                MetricRow("Strict Guardrails", snapshot.complianceMode.strictGuardrails.toString())
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(
                        onClick = viewModel::enableManualOnlyCompliance,
                        enabled = !state.isSaving,
                        modifier = Modifier.weight(1f)
                    ) { Text("Manual-only") }
                    Button(
                        onClick = viewModel::enableStrictGuardrailCompliance,
                        enabled = !state.isSaving,
                        modifier = Modifier.weight(1f)
                    ) { Text("Strict") }
                }
                Text("Audit Export Preview", fontWeight = FontWeight.SemiBold)
                Text(
                    snapshot.auditExportJson?.take(1000) ?: "No export",
                    style = MaterialTheme.typography.bodySmall,
                    color = Color(0xFFB0BEC5)
                )
            }

            TerminalCard(title = "Live Autonomous Feed") {
                OutlinedTextField(
                    value = state.symbolFilter,
                    onValueChange = viewModel::updateSymbolFilter,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Feed Symbol Filter") },
                    singleLine = true
                )
                Button(onClick = viewModel::refresh, modifier = Modifier.fillMaxWidth(), enabled = !state.isSaving) {
                    Text("Refresh Feed")
                }

                val feed = snapshot.feed.take(20)
                if (feed.isEmpty()) {
                    Text("No autonomous feed events yet")
                } else {
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxWidth()
                            .heightIn(min = 120.dp, max = 340.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(feed) { item ->
                            TerminalCard(title = "${item.symbol} • ${item.status}") {
                                MetricRow("Strategy", item.strategy)
                                MetricRow("Confidence", "${(item.confidence * 100).toInt()}%")
                                MetricRow("PnL", item.pnl?.let { String.format("%.2f", it) } ?: "-")
                                Text(item.why, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                }
            }
        }
    }
}
