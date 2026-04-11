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
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ghost.alpha.presentation.components.MetricRow
import com.ghost.alpha.presentation.components.TerminalCard
import com.ghost.alpha.presentation.viewmodel.BacktestViewModel

@Composable
fun BacktestingScreen(viewModel: BacktestViewModel) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("Backtesting Lab", style = MaterialTheme.typography.headlineMedium)
        OutlinedTextField(
            value = state.symbol,
            onValueChange = viewModel::updateSymbol,
            modifier = Modifier.fillMaxWidth(),
            label = { Text("Symbol") },
            singleLine = true
        )
        Button(onClick = viewModel::runBacktest, modifier = Modifier.fillMaxWidth()) {
            Text(if (state.isLoading) "Running..." else "Run Simulation")
        }
        state.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        TerminalCard(title = "Results") {
            state.result?.let { result ->
                MetricRow("Ending Balance", "$${"%.2f".format(result.endingBalance)}")
                MetricRow("Win Rate", "${(result.winRate * 100).toInt()}%")
                MetricRow("Total Trades", result.totalTrades.toString())
                MetricRow("Sharpe", "${"%.2f".format(result.sharpeRatio)}")
                MetricRow("Max Drawdown", "${"%.2f".format(result.maxDrawdown)}")
            } ?: Text("No backtest result yet")
        }
    }
}