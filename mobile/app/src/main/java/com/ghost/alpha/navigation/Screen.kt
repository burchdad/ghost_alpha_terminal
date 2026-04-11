package com.ghost.alpha.navigation

sealed class Screen(val route: String, val label: String) {
    data object Login : Screen("login", "Login")
    data object TwoFactor : Screen("two_factor", "2FA")
    data object Dashboard : Screen("dashboard", "Dashboard")
    data object Swarm : Screen("swarm", "Swarm")
    data object Trading : Screen("trading", "Trade")
    data object Brokers : Screen("brokers", "Brokers")
    data object Backtest : Screen("backtest", "Backtest")
}

val primaryScreens = listOf(
    Screen.Dashboard,
    Screen.Swarm,
    Screen.Trading,
    Screen.Brokers,
    Screen.Backtest
)