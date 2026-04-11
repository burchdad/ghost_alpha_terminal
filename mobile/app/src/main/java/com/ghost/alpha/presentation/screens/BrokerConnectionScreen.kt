package com.ghost.alpha.presentation.screens

import androidx.browser.customtabs.CustomTabsIntent
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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ghost.alpha.presentation.components.MetricRow
import com.ghost.alpha.presentation.components.TerminalCard
import com.ghost.alpha.presentation.viewmodel.BrokerViewModel

@Composable
fun BrokerConnectionScreen(viewModel: BrokerViewModel, initialDeepLink: String?) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current

    LaunchedEffect(initialDeepLink) {
        viewModel.onCallback(initialDeepLink)
    }

    LaunchedEffect(state.pendingConnectUrl) {
        state.pendingConnectUrl?.let { url ->
            CustomTabsIntent.Builder().build().launchUrl(context, android.net.Uri.parse(url))
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        Text("Broker Access", style = MaterialTheme.typography.headlineMedium)
        state.errorMessage?.let { Text(it, color = MaterialTheme.colorScheme.error) }

        state.brokers.forEach { broker ->
            TerminalCard(title = broker.label) {
                MetricRow("Provider", broker.provider)
                MetricRow("Connected", broker.connected.toString())
                MetricRow("Configured", broker.configured.toString())
                MetricRow("Accounts", broker.accounts.joinToString().ifBlank { "None" })
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                    Button(onClick = { viewModel.prepareConnect(broker.provider) }, modifier = Modifier.weight(1f), enabled = broker.provider == "alpaca") {
                        Text("Connect")
                    }
                    Button(onClick = { viewModel.disconnect(broker.provider) }, modifier = Modifier.weight(1f), enabled = broker.connected) {
                        Text("Disconnect")
                    }
                }
            }
        }

        state.callbackState?.let {
            TerminalCard(title = "OAuth Callback") {
                Text(it, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}