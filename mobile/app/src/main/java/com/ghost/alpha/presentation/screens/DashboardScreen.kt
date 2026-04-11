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
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ghost.alpha.presentation.components.ConfidenceMeter
import com.ghost.alpha.presentation.components.MetricRow
import com.ghost.alpha.presentation.components.SignalBadge
import com.ghost.alpha.presentation.components.TerminalCard
import com.ghost.alpha.presentation.viewmodel.DashboardViewModel

@Composable
fun DashboardScreen(
    viewModel: DashboardViewModel,
    onOpenSwarm: () -> Unit,
    onOpenTrade: () -> Unit
) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("Mission Dashboard", style = MaterialTheme.typography.headlineMedium)
        state.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        TerminalCard(title = "Portfolio Pulse") {
            val portfolio = state.portfolio
            MetricRow("Balance", portfolio?.accountBalance?.let { "$${"%.2f".format(it)}" } ?: "--")
            MetricRow("Buying Power", portfolio?.availableBuyingPower?.let { "$${"%.2f".format(it)}" } ?: "--")
            MetricRow("Active Positions", portfolio?.positions?.size?.toString() ?: "0")
            MetricRow("Risk Exposure", portfolio?.riskExposurePct?.let { "${(it * 100).toInt()}%" } ?: "--")
        }

        TerminalCard(title = "Featured Signal") {
            state.featuredSignal?.let { signal ->
                SignalBadge(signal.signal)
                ConfidenceMeter(signal.confidence)
                Text(signal.reasoning, color = MaterialTheme.colorScheme.onSurfaceVariant)
            } ?: Text("No signal loaded")
        }

        TerminalCard(title = "Swarm Snapshot") {
            state.featuredSwarm?.let { swarm ->
                SignalBadge(swarm.signal)
                MetricRow("Regime", swarm.regime)
                MetricRow("Top Strategy", swarm.topStrategy)
                MetricRow("Expected Value", "${"%.2f".format(swarm.expectedValue)}")
                ConfidenceMeter(swarm.confidence)
            } ?: Text("Swarm data unavailable")
        }

        TerminalCard(title = "Live Alerts") {
            if (state.alerts.isEmpty()) {
                Text("No alerts yet")
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    state.alerts.forEach { alert ->
                        Column {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text(alert.title)
                                Text(alert.severity.uppercase(), color = MaterialTheme.colorScheme.primary)
                            }
                            Text(alert.message, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }

        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Button(onClick = onOpenSwarm, modifier = Modifier.weight(1f)) { Text("Open Swarm") }
            Button(onClick = onOpenTrade, modifier = Modifier.weight(1f)) { Text("Trade") }
        }
    }
}