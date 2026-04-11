package com.ghost.alpha.presentation.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ghost.alpha.presentation.components.TerminalCard
import com.ghost.alpha.presentation.viewmodel.AuthViewModel

@Composable
fun TwoFactorScreen(viewModel: AuthViewModel) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp)
    ) {
        Text("Step-Up Verification", style = MaterialTheme.typography.headlineMedium)
        Text(
            "Complete ${state.pendingMethod ?: "OTP"} verification to unlock high-trust actions.",
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        TerminalCard(title = "2FA Challenge") {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = state.otpCode,
                    onValueChange = viewModel::updateOtp,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Verification Code") },
                    singleLine = true
                )
                androidx.compose.foundation.layout.Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("Trust this device")
                    Switch(checked = state.trustDevice, onCheckedChange = viewModel::updateTrustDevice)
                }
                state.errorMessage?.let { error ->
                    Text(error, color = MaterialTheme.colorScheme.error)
                }
                Button(
                    onClick = viewModel::verifyTwoFactor,
                    enabled = !state.isLoading && state.otpCode.isNotBlank(),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(if (state.isLoading) "Verifying..." else "Confirm")
                }
            }
        }
    }
}