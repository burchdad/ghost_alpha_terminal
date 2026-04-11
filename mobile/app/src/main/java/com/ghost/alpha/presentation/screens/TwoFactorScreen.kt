package com.ghost.alpha.presentation.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
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
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.ghost.alpha.presentation.components.ErrorBanner
import com.ghost.alpha.presentation.components.LoadingRow
import com.ghost.alpha.presentation.components.TerminalCard
import com.ghost.alpha.presentation.viewmodel.AuthViewModel
import com.ghost.alpha.utils.BiometricStepUpManager

@Composable
fun TwoFactorScreen(viewModel: AuthViewModel) {
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val activity = context as? FragmentActivity
    val biometricManager = remember(activity) { activity?.let { BiometricStepUpManager(it) } }

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
        if (state.isLoading) {
            LoadingRow("Validating high-trust session...")
        }
        state.errorMessage?.let { error ->
            ErrorBanner(message = error, onRetry = viewModel::verifyTwoFactor)
        }
        state.biometricErrorMessage?.let { error ->
            ErrorBanner(message = error)
        }

        TerminalCard(title = "2FA Challenge") {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                OutlinedTextField(
                    value = state.otpCode,
                    onValueChange = viewModel::updateOtp,
                    modifier = Modifier.fillMaxWidth(),
                    label = { Text("Verification Code") },
                    singleLine = true
                )
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("Trust this device")
                    Switch(checked = state.trustDevice, onCheckedChange = viewModel::updateTrustDevice)
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text("Require biometric step-up")
                    Switch(
                        checked = state.requireBiometricStepUp,
                        onCheckedChange = viewModel::updateRequireBiometricStepUp
                    )
                }
                if (state.requireBiometricStepUp && biometricManager != null) {
                    Button(
                        onClick = {
                            if (biometricManager.isAvailable()) {
                                biometricManager.authenticate(
                                    onSuccess = viewModel::onBiometricVerified,
                                    onError = viewModel::onBiometricFailed
                                )
                            } else {
                                viewModel.onBiometricFailed("Biometric authentication is unavailable on this device")
                            }
                        },
                        enabled = !state.isLoading,
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(if (state.biometricVerified) "Biometric Verified" else "Verify Biometrics")
                    }
                }
                Button(
                    onClick = viewModel::verifyTwoFactor,
                    enabled = !state.isLoading && state.otpCode.isNotBlank() &&
                        (!state.requireBiometricStepUp || state.biometricVerified),
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Text(if (state.isLoading) "Verifying..." else "Confirm")
                }
            }
        }
    }
}