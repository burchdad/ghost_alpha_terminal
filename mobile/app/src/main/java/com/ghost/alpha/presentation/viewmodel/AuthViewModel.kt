package com.ghost.alpha.presentation.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.ghost.alpha.domain.repository.AuthRepository
import com.ghost.alpha.domain.usecase.LoginUseCase
import com.ghost.alpha.domain.usecase.VerifyTwoFactorUseCase
import com.ghost.alpha.utils.toUserMessage
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class AuthUiState(
    val email: String = "",
    val password: String = "",
    val otpCode: String = "",
    val trustDevice: Boolean = true,
    val isLoading: Boolean = false,
    val isAuthenticated: Boolean = false,
    val requiresTwoFactor: Boolean = false,
    val pendingMethod: String? = null,
    val requireBiometricStepUp: Boolean = false,
    val biometricVerified: Boolean = false,
    val biometricErrorMessage: String? = null,
    val errorMessage: String? = null
)

@HiltViewModel
class AuthViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val loginUseCase: LoginUseCase,
    private val verifyTwoFactorUseCase: VerifyTwoFactorUseCase
) : ViewModel() {
    private val _uiState = MutableStateFlow(AuthUiState())
    val uiState: StateFlow<AuthUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            authRepository.session.collect { session ->
                _uiState.update {
                    it.copy(
                        isAuthenticated = session.isAuthenticated,
                        requiresTwoFactor = session.user?.stepUpRequired == true || session.pendingStepUpMethod != null,
                        pendingMethod = session.pendingStepUpMethod,
                        isLoading = false
                    )
                }
            }
        }
    }

    fun updateEmail(value: String) {
        _uiState.update { it.copy(email = value, errorMessage = null) }
    }

    fun updatePassword(value: String) {
        _uiState.update { it.copy(password = value, errorMessage = null) }
    }

    fun updateOtp(value: String) {
        _uiState.update { it.copy(otpCode = value, errorMessage = null) }
    }

    fun updateTrustDevice(value: Boolean) {
        _uiState.update { it.copy(trustDevice = value) }
    }

    fun updateRequireBiometricStepUp(value: Boolean) {
        _uiState.update {
            it.copy(
                requireBiometricStepUp = value,
                biometricVerified = if (value) it.biometricVerified else false,
                biometricErrorMessage = null
            )
        }
    }

    fun onBiometricVerified() {
        _uiState.update { it.copy(biometricVerified = true, biometricErrorMessage = null) }
    }

    fun onBiometricFailed(message: String) {
        _uiState.update { it.copy(biometricVerified = false, biometricErrorMessage = message) }
    }

    fun login() {
        viewModelScope.launch {
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            runCatching { loginUseCase(_uiState.value.email.trim(), _uiState.value.password) }
                .onFailure { error ->
                    _uiState.update { it.copy(isLoading = false, errorMessage = error.toUserMessage()) }
                }
        }
    }

    fun verifyTwoFactor() {
        viewModelScope.launch {
            if (_uiState.value.requireBiometricStepUp && !_uiState.value.biometricVerified) {
                _uiState.update {
                    it.copy(
                        isLoading = false,
                        biometricErrorMessage = "Biometric verification required before OTP confirmation."
                    )
                }
                return@launch
            }
            _uiState.update { it.copy(isLoading = true, errorMessage = null) }
            runCatching { verifyTwoFactorUseCase(_uiState.value.otpCode.trim(), _uiState.value.trustDevice) }
                .onFailure { error ->
                    _uiState.update { it.copy(isLoading = false, errorMessage = error.toUserMessage()) }
                }
        }
    }

    fun logout() {
        viewModelScope.launch {
            authRepository.logout()
        }
    }
}