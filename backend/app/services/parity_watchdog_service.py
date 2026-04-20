from __future__ import annotations

from app.core.config import settings
from app.services.brokers.router import broker_router
from app.services.live_portfolio_service import live_portfolio_service
from app.services.portfolio_manager import portfolio_manager
from app.services.swarm.execution_bridge import execution_bridge


class ParityWatchdogService:
    """Detect drift between expected broker routing/runtime mode and account snapshots."""

    def status(self) -> dict:
        mode = execution_bridge.get_mode()
        issues: list[str] = []
        checks: list[dict] = []

        if mode == "LIVE_TRADING" and settings.alpaca_paper:
            issues.append(
                "LIVE_TRADING mode active while ALPACA_PAPER=true. Alpaca-routed symbols will stay paper until ALPACA_PAPER=false."
            )

        if mode == "LIVE_TRADING" and (not settings.coinbase_api_key_name or not settings.coinbase_api_private_key):
            issues.append("LIVE_TRADING enabled but Coinbase credentials are missing.")

        if mode == "LIVE_TRADING" and (not settings.tradier_effective_api_key or not settings.tradier_effective_account_number):
            issues.append("LIVE_TRADING enabled but Tradier credentials are missing for equity routing.")

        allowlist = [item.strip().upper() for item in settings.coinbase_trade_products.split(",") if item.strip()]
        if not allowlist:
            issues.append("Coinbase allowlist is empty.")

        sample_symbols = ["BTCUSD", "ETHUSD", "SPY", "AAPL"]
        for symbol in sample_symbols:
            expected = broker_router.route_broker(symbol=symbol, liquidity_score=1.0, mode=mode)
            checks.append({"symbol": symbol, "expected_broker": expected})

        live = live_portfolio_service.snapshot() or {}
        shadow = portfolio_manager.snapshot() or {}
        live_balance = float(live.get("account_balance", 0.0) or 0.0)
        shadow_balance = float(shadow.get("account_balance", 0.0) or 0.0)
        if abs(live_balance - shadow_balance) > max(250.0, live_balance * 0.03):
            issues.append("Portfolio snapshot mismatch between live and internal shadow ledger.")

        broker_accounts = live.get("broker_accounts") or []
        coinbase_connected = any(
            item.get("broker") == "coinbase" and bool(item.get("connected"))
            for item in broker_accounts
        )
        tradier_connected = any(
            item.get("broker") == "tradier" and bool(item.get("connected"))
            for item in broker_accounts
        )
        if mode == "LIVE_TRADING" and not coinbase_connected:
            issues.append("LIVE_TRADING expects Coinbase route for crypto, but Coinbase account is not connected.")
        if mode == "LIVE_TRADING" and not tradier_connected:
            issues.append("LIVE_TRADING expects Tradier route for equities, but Tradier account is not connected.")

        if len(issues) >= 3:
            level = "RED"
        elif issues:
            level = "YELLOW"
        else:
            level = "GREEN"

        return {
            "status": level,
            "mode": mode,
            "issues": issues,
            "route_expectations": checks,
            "live_balance": round(live_balance, 2),
            "shadow_balance": round(shadow_balance, 2),
        }


parity_watchdog_service = ParityWatchdogService()
