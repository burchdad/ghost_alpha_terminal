package com.ghost.alpha.navigation

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.ghost.alpha.presentation.screens.BacktestingScreen
import com.ghost.alpha.presentation.screens.BrokerConnectionScreen
import com.ghost.alpha.presentation.screens.CopilotCommandScreen
import com.ghost.alpha.presentation.screens.DashboardScreen
import com.ghost.alpha.presentation.screens.LoginScreen
import com.ghost.alpha.presentation.screens.PerformanceIntelligenceScreen
import com.ghost.alpha.presentation.screens.SwarmTerminalScreen
import com.ghost.alpha.presentation.screens.TradingScreen
import com.ghost.alpha.presentation.screens.TradeGuardrailsScreen
import com.ghost.alpha.presentation.screens.TwoFactorScreen
import com.ghost.alpha.presentation.viewmodel.AuthViewModel
import com.ghost.alpha.presentation.viewmodel.BacktestViewModel
import com.ghost.alpha.presentation.viewmodel.BrokerViewModel
import com.ghost.alpha.presentation.viewmodel.DashboardViewModel
import com.ghost.alpha.presentation.viewmodel.PerformanceViewModel
import com.ghost.alpha.presentation.viewmodel.SwarmViewModel
import com.ghost.alpha.presentation.viewmodel.TradingViewModel

@Composable
fun GhostAlphaRoot(initialDeepLink: String?) {
    val navController = rememberNavController()
    val authViewModel: AuthViewModel = hiltViewModel()
    val authState by authViewModel.uiState.collectAsStateWithLifecycle()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = navBackStackEntry?.destination
    val currentRoute = currentDestination?.route

    LaunchedEffect(authState.isAuthenticated, authState.requiresTwoFactor) {
        when {
            authState.requiresTwoFactor && currentRoute != Screen.TwoFactor.route -> {
                navController.navigate(Screen.TwoFactor.route)
            }

            authState.isAuthenticated && !authState.requiresTwoFactor && currentRoute != Screen.Dashboard.route -> {
                navController.navigate(Screen.Dashboard.route) {
                    popUpTo(Screen.Login.route) { inclusive = true }
                    launchSingleTop = true
                }
            }

            !authState.isAuthenticated && currentRoute !in listOf(Screen.Login.route, Screen.TwoFactor.route) -> {
                navController.navigate(Screen.Login.route) {
                    popUpTo(0) { inclusive = true }
                    launchSingleTop = true
                }
            }
        }
    }

    Scaffold(
        bottomBar = {
            if (currentRoute in primaryScreens.map { it.route }) {
                NavigationBar {
                    primaryScreens.forEach { screen ->
                        NavigationBarItem(
                            selected = currentDestination?.hierarchy?.any { it.route == screen.route } == true,
                            onClick = {
                                navController.navigate(screen.route) {
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Text(screen.label.take(1)) },
                            label = { Text(screen.label) }
                        )
                    }
                }
            }
        }
    ) { innerPadding ->
        NavHost(
            navController = navController,
            startDestination = Screen.Login.route,
            modifier = Modifier.padding(innerPadding)
        ) {
            composable(Screen.Login.route) {
                LoginScreen(viewModel = authViewModel)
            }
            composable(Screen.TwoFactor.route) {
                TwoFactorScreen(viewModel = authViewModel)
            }
            composable(Screen.Dashboard.route) {
                val viewModel: DashboardViewModel = hiltViewModel()
                DashboardScreen(
                    viewModel = viewModel,
                    onOpenSwarm = { navController.navigate(Screen.Swarm.route) },
                    onOpenTrade = { navController.navigate(Screen.Trading.route) }
                )
            }
            composable(Screen.Swarm.route) {
                val viewModel: SwarmViewModel = hiltViewModel()
                SwarmTerminalScreen(viewModel = viewModel)
            }
            composable(Screen.Trading.route) {
                val viewModel: TradingViewModel = hiltViewModel()
                TradingScreen(viewModel = viewModel)
            }
            composable(Screen.Brokers.route) {
                val viewModel: BrokerViewModel = hiltViewModel()
                BrokerConnectionScreen(viewModel = viewModel, initialDeepLink = initialDeepLink)
            }
            composable(Screen.Backtest.route) {
                val viewModel: BacktestViewModel = hiltViewModel()
                BacktestingScreen(viewModel = viewModel)
            }
            composable(Screen.TradeGuardrails.route) {
                TradeGuardrailsScreen()
            }
            composable(Screen.Copilot.route) {
                CopilotCommandScreen()
            }
            composable(Screen.Performance.route) {
                val viewModel: PerformanceViewModel = hiltViewModel()
                PerformanceIntelligenceScreen(viewModel = viewModel)
            }
        }
    }
}