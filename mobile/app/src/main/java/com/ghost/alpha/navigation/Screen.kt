package com.ghost.alpha.navigation

sealed class Screen(val route: String, val label: String) {
    data object Login : Screen("login", "Login")
    data object TwoFactor : Screen("two_factor", "2FA")
    data object Dashboard : Screen("dashboard", "Dashboard")
    data object Swarm : Screen("swarm", "Swarm")
    data object Trading : Screen("trading", "Trade")
    data object Brokers : Screen("brokers", "Brokers")
    data object Backtest : Screen("backtest", "Backtest")
    data object TradeGuardrails : Screen("guardrails", "Guardrails")
    data object Copilot : Screen("copilot", "Copilot")
    data object Performance : Screen("performance", "Performance")
    data object AuditTrail : Screen("audit_trail", "Audit")
}

val primaryScreens = listOf(
    Screen.Dashboard,
    Screen.Swarm,
    Screen.Trading,
    Screen.Brokers,
    Screen.Backtest,
    Screen.TradeGuardrails,
    Screen.Copilot,
    Screen.Performance,
    Screen.AuditTrail
)