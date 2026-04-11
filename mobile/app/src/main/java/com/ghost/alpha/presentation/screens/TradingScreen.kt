package com.ghost.alpha.presentation.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ghost.alpha.presentation.components.MetricRow
import com.ghost.alpha.presentation.components.SignalBadge
import com.ghost.alpha.presentation.components.TerminalCard
import com.ghost.alpha.presentation.viewmodel.TradingViewModel

@Composable
fun TradingScreen(viewModel: TradingViewModel) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("Execution Console", style = MaterialTheme.typography.headlineMedium)

        TerminalCard(title = "Trade Parameters") {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(state.symbol, viewModel::updateSymbol, modifier = Modifier.fillMaxWidth(), label = { Text("Symbol") }, singleLine = true)
                OutlinedTextField(state.strategy, viewModel::updateStrategy, modifier = Modifier.fillMaxWidth(), label = { Text("Strategy") }, singleLine = true)
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    OutlinedTextField(state.side, viewModel::updateSide, modifier = Modifier.weight(1f), label = { Text("Side") }, singleLine = true)
                    OutlinedTextField(state.entryPrice, viewModel::updateEntryPrice, modifier = Modifier.weight(1f), label = { Text("Entry") }, singleLine = true)
                }
                OutlinedTextField(state.confidence, viewModel::updateConfidence, modifier = Modifier.fillMaxWidth(), label = { Text("Confidence") }, singleLine = true)
                Row(horizontalArrangement = Arrangement.spacedBy(12.dp), modifier = Modifier.fillMaxWidth()) {
                    Button(onClick = viewModel::loadSignal, modifier = Modifier.weight(1f)) { Text("Pull Signal") }
                    Button(onClick = viewModel::executeTrade, modifier = Modifier.weight(1f)) { Text(if (state.isLoading) "Submitting..." else "Execute") }
                }
            }
        }

        TerminalCard(title = "Signal Context") {
            state.latestSignal?.let { SignalBadge(it) } ?: Text("No signal loaded")
            state.latestConfidence?.let { MetricRow("Signal Confidence", "${(it * 100).toInt()}%") }
        }

        TerminalCard(title = "Execution Result") {
            state.result?.let { result ->
                MetricRow("Accepted", result.accepted.toString())
                MetricRow("Risk Level", result.riskLevel)
                MetricRow("Position Size", "${"%.4f".format(result.positionSize)}")
                MetricRow("Expected Value", "${"%.2f".format(result.expectedValue)}")
                result.reason?.let { Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant) }
            } ?: Text("No execution submitted yet")
        }

        state.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }
    }
}