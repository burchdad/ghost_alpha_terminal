package com.ghost.alpha.presentation.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.HorizontalDivider
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
import com.ghost.alpha.presentation.components.ConfidenceHeatmap
import com.ghost.alpha.presentation.components.ConfidenceMeter
import com.ghost.alpha.presentation.components.ErrorBanner
import com.ghost.alpha.presentation.components.LoadingRow
import com.ghost.alpha.presentation.components.MetricRow
import com.ghost.alpha.presentation.components.SignalBadge
import com.ghost.alpha.presentation.components.SkeletonTerminalCard
import com.ghost.alpha.presentation.components.SwarmNodeGraph
import com.ghost.alpha.presentation.components.TerminalCard
import com.ghost.alpha.presentation.viewmodel.SwarmViewModel

@Composable
fun SwarmTerminalScreen(viewModel: SwarmViewModel) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("Swarm Terminal", style = MaterialTheme.typography.headlineMedium)
        OutlinedTextField(
            value = state.symbol,
            onValueChange = viewModel::updateSymbol,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Symbol") },
            singleLine = true
        )
        Button(onClick = viewModel::refresh, modifier = Modifier.fillMaxWidth()) {
            Text(if (state.isLoading) "Refreshing..." else "Refresh Consensus")
        }
        if (state.isLoading) {
            LoadingRow("Pulling agent consensus...")
        }
        state.errorMessage?.let { ErrorBanner(message = it, onRetry = viewModel::refresh) }

        if (state.isLoading && state.swarmSignal == null) {
            SkeletonTerminalCard(title = "Consensus", rows = 4)
            SkeletonTerminalCard(title = "Agent Breakdown", rows = 5)
        }

        TerminalCard(title = "Consensus") {
            state.swarmSignal?.let { swarm ->
                SignalBadge(swarm.signal)
                MetricRow("Regime", swarm.regime)
                MetricRow("Top Strategy", swarm.topStrategy)
                MetricRow("Risk Level", swarm.riskLevel)
                ConfidenceMeter(swarm.confidence)
                HorizontalDivider(color = MaterialTheme.colorScheme.primary.copy(alpha = 0.18f))
                MetricRow("Dominant Bias", state.dominantBias)
                MetricRow("Agreement", "${(state.agreementRatio * 100).toInt()}%")
                MetricRow("Conflict", "${(state.conflictRatio * 100).toInt()}%")
            } ?: Text("No swarm signal loaded")
        }

        TerminalCard(title = "Swarm Topology") {
            val votes = state.swarmSignal?.agents.orEmpty()
            if (votes.isEmpty()) {
                Text("Awaiting graph topology")
            } else {
                SwarmNodeGraph(
                    agents = votes,
                    consensusSignal = state.swarmSignal?.signal.orEmpty()
                )
            }
        }

        TerminalCard(title = "Confidence Heatmap") {
            ConfidenceHeatmap(agents = state.swarmSignal?.agents.orEmpty())
        }

        TerminalCard(title = "Agent Breakdown") {
            val votes = state.swarmSignal?.agents.orEmpty()
            if (votes.isEmpty()) {
                Text("Awaiting agent output")
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    votes.forEach { vote ->
                        Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            MetricRow(vote.name, "${(vote.confidence * 100).toInt()}% ${vote.bias}")
                            Text(vote.reasoning, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }
    }
}