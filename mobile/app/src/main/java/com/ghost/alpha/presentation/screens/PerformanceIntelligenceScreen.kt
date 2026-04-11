package com.ghost.alpha.presentation.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ghost.alpha.domain.model.PerformanceIntelligenceSnapshot
import com.ghost.alpha.presentation.components.ErrorBanner
import com.ghost.alpha.presentation.components.LoadingRow
import com.ghost.alpha.presentation.components.MetricRow
import com.ghost.alpha.presentation.components.SkeletonTerminalCard
import com.ghost.alpha.presentation.components.TerminalCard
import com.ghost.alpha.presentation.viewmodel.PerformanceViewModel

@Composable
fun PerformanceIntelligenceScreen(viewModel: PerformanceViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    var daysInput by remember(state.days) { mutableStateOf(state.days.toString()) }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("Performance Intelligence", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)

        OutlinedTextField(
            value = state.symbol,
            onValueChange = viewModel::updateSymbol,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Symbol Insight") },
            singleLine = true
        )
        OutlinedTextField(
            value = daysInput,
            onValueChange = {
                daysInput = it
                viewModel.updateDays(it)
            },
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Window Days (1-30)") },
            singleLine = true
        )
        Button(onClick = viewModel::refresh, modifier = Modifier.fillMaxWidth()) {
            Text(if (state.isLoading) "Refreshing..." else "Refresh Intelligence")
        }

        if (state.isLoading) {
            LoadingRow("Computing performance intelligence...")
        }
        state.errorMessage?.let { ErrorBanner(message = it, onRetry = viewModel::refresh) }

        if (state.isLoading && state.snapshot == null) {
            SkeletonTerminalCard(title = "Summary", rows = 4)
            SkeletonTerminalCard(title = "Strategy Scoreboard", rows = 5)
        }

        state.snapshot?.let { snapshot ->
            SummaryCard(snapshot)
            StrategyScoreboardCard(snapshot)
            AgentLeadersCard(snapshot)
            ExecutionFeedCard(snapshot)
        }
    }
}

@Composable
private fun SummaryCard(snapshot: PerformanceIntelligenceSnapshot) {
    TerminalCard(title = "Trading Truth Summary") {
        MetricRow("Window", "${snapshot.windowDays} days")
        MetricRow("Trades", snapshot.trades.toString())
        MetricRow("Settled Trades", snapshot.settledTrades.toString())
        MetricRow("Win Rate", "${(snapshot.winRate * 100).toInt()}%")
        MetricRow("Net PnL", String.format("%.2f", snapshot.netPnl))
        MetricRow("Best Strategy", snapshot.bestStrategy?.strategy ?: "n/a")
        MetricRow("Worst Strategy", snapshot.worstStrategy?.strategy ?: "n/a")
    }
}

@Composable
private fun StrategyScoreboardCard(snapshot: PerformanceIntelligenceSnapshot) {
    TerminalCard(title = "Strategy Scoreboard") {
        if (snapshot.strategyBreakdown.isEmpty()) {
            Text("No settled strategy data yet")
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                snapshot.strategyBreakdown.take(8).forEach { stat ->
                    MetricRow(stat.strategy, "Win ${(stat.winRate * 100).toInt()}% | PnL ${String.format("%.2f", stat.netPnl)}")
                }
            }
        }
    }
}

@Composable
private fun AgentLeadersCard(snapshot: PerformanceIntelligenceSnapshot) {
    TerminalCard(title = "Agent Leaders") {
        val topAgents = snapshot.symbolInsight?.topAgents.orEmpty()
        if (topAgents.isEmpty()) {
            Text("No symbol-level agent leaderboard available")
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                MetricRow("Best Agent", snapshot.symbolInsight?.bestAgent ?: "n/a")
                topAgents.take(6).forEach { agent ->
                    MetricRow(
                        agent.agentName,
                        "WR ${(agent.winRate * 100).toInt()}% | Score ${(agent.compositeScore * 100).toInt()}%"
                    )
                }
            }
        }
    }
}

@Composable
private fun ExecutionFeedCard(snapshot: PerformanceIntelligenceSnapshot) {
    TerminalCard(title = "Recent Execution Intelligence") {
        val executions = snapshot.recentExecutions.take(8)
        if (executions.isEmpty()) {
            Text("No executions recorded")
        } else {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                executions.forEach { item ->
                    val outcome = item.outcomeLabel ?: if (item.submitted) "SUBMITTED" else "REJECTED"
                    val pnlText = item.pnl?.let { String.format("%.2f", it) } ?: "-"
                    MetricRow(
                        "${item.symbol} ${item.strategy}",
                        "$outcome | Conf ${(item.confidence * 100).toInt()}% | PnL $pnlText"
                    )
                }
            }
        }
    }
}
