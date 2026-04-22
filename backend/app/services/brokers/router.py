from __future__ import annotations

from threading import Lock

from app.core.config import settings
from app.services.brokers.alpaca_adapter import alpaca_broker_adapter
from app.services.brokers.base import BrokerAdapter, BrokerOrderRequest, BrokerOrderResult
from app.services.brokers.coinbase_adapter import coinbase_broker_adapter
from app.services.brokers.schwab_adapter import schwab_broker_adapter
from app.services.brokers.tradier_adapter import tradier_broker_adapter
from app.services.schwab_client import schwab_client

# Planned broker integrations — OAuth applications in-flight or not yet submitted.
# These are surfaced in the UI as "Integration Planned" to track pipeline status.
PLANNED_BROKERS: dict[str, dict] = {
    "tastytrade": {
        "label": "tastytrade",
        "supports_equities": True,
        "supports_crypto": False,
        "supports_options": True,
        "supports_fractional": False,
        "supports_leverage": True,
        "planned": True,
        "oauth_url": "https://developer.tastytrade.com",
        "notes": "Options- and futures-focused broker with an open REST API. Apply at developer.tastytrade.com.",
    },
    "robinhood": {
        "label": "Robinhood",
        "supports_equities": True,
        "supports_crypto": True,
        "supports_options": True,
        "supports_fractional": True,
        "supports_leverage": False,
        "planned": True,
        "oauth_url": "https://robinhood.com/about/developer-api",
        "notes": "Commission-free equities, crypto, and options with an OAuth developer API program.",
    },
    "tradestation": {
        "label": "TradeStation",
        "supports_equities": True,
        "supports_crypto": False,
        "supports_options": True,
        "supports_fractional": False,
        "supports_leverage": True,
        "planned": True,
        "oauth_url": "https://api.tradestation.com",
        "notes": "Equities, options, and futures broker. OAuth developer access available at api.tradestation.com.",
    },
}


class BrokerRouter:
    def __init__(self) -> None:
        self._adapters: dict[str, BrokerAdapter] = {
            "alpaca": alpaca_broker_adapter,
            "coinbase": coinbase_broker_adapter,
            "schwab": schwab_broker_adapter,
            "tradier": tradier_broker_adapter,
        }
        self._rr_lock = Lock()
        self._rr_counters: dict[str, int] = {}

    @staticmethod
    def _parse_weight_spec(raw: str) -> dict[str, int]:
        weights: dict[str, int] = {}
        for token in raw.split(","):
            part = token.strip()
            if not part or "=" not in part:
                continue
            broker, value = part.split("=", 1)
            broker_name = broker.strip().lower()
            try:
                weight = int(value.strip())
            except ValueError:
                continue
            if broker_name and weight > 0:
                weights[broker_name] = min(weight, 10)
        return weights

    def _weighted_round_robin(self, *, bucket: str, candidates: list[str], weights: dict[str, int]) -> str:
        if len(candidates) == 1:
            return candidates[0]

        expanded: list[str] = []
        for name in candidates:
            expanded.extend([name] * max(1, int(weights.get(name, 1))))
        if not expanded:
            return candidates[0]

        with self._rr_lock:
            counter = self._rr_counters.get(bucket, 0)
            selected = expanded[counter % len(expanded)]
            self._rr_counters[bucket] = counter + 1
        return selected

    def capabilities_map(self) -> dict[str, dict]:
        result: dict[str, dict] = {
            name: adapter.capabilities().__dict__
            for name, adapter in self._adapters.items()
        }
        result.update(PLANNED_BROKERS)
        return result

    def routing_policy_summary(self, *, user_id: str | None = None) -> dict:
        tradier_ready = bool(
            settings.tradier_live_trading_enabled
            and settings.tradier_effective_api_key
            and settings.tradier_effective_account_number
        )
        alpaca_live_ready = bool(
            settings.alpaca_api_key
            and settings.alpaca_secret_key
            and not settings.alpaca_paper
        )
        alpaca_any_ready = bool(settings.alpaca_api_key and settings.alpaca_secret_key)
        coinbase_ready = bool(
            settings.coinbase_live_trading_enabled
            and settings.coinbase_api_key_name
            and settings.coinbase_api_private_key
        )
        schwab_configured = bool(
            settings.schwab_client_id
            and settings.schwab_client_secret
            and settings.schwab_redirect_uri
        )
        schwab_ready = bool(user_id and schwab_client.is_connected(user_id=user_id))
        option_candidates = [name for name, ready in (("tradier", tradier_ready), ("schwab", schwab_ready)) if ready]

        return {
            "policy": {
                "equity_live": settings.broker_equity_live_policy.strip().lower(),
                "equity_live_weights": self._parse_weight_spec(settings.broker_equity_live_weights),
                "option_live_weights": self._parse_weight_spec(settings.broker_option_live_weights),
                "crypto_live_weights": self._parse_weight_spec(settings.broker_crypto_live_weights),
            },
            "brokers": {
                "tradier": {
                    "execution_ready": tradier_ready,
                    "strengths": ["live equities", "options execution", "multi-leg options routing"],
                    "preferred_for": ["LIVE_TRADING equities", "options strategies"],
                },
                "alpaca": {
                    "execution_ready": alpaca_any_ready,
                    "strengths": ["paper trading", "fractional equities", "equity fallback execution"],
                    "preferred_for": ["PAPER_TRADING equities", "balanced live equity fallback"],
                },
                "coinbase": {
                    "execution_ready": coinbase_ready,
                    "strengths": ["crypto execution", "public websocket signal augmentation"],
                    "preferred_for": ["LIVE_TRADING crypto", "crypto market data"],
                },
                "schwab": {
                    "execution_ready": schwab_ready,
                    "configured": schwab_configured,
                    "strengths": ["oauth account coverage", "portfolio visibility", "market and options data", "single-order execution"],
                    "preferred_for": ["user-scoped live equities", "user-scoped single-leg options", "account aggregation"],
                    "constraint": (
                        "Connect Schwab and execute from an authenticated user context to include it in weighted routing."
                        if not schwab_ready
                        else "Available for connected user-scoped execution; advanced multi-leg options still route through Tradier options_execution_service."
                    ),
                },
            },
            "strategy_routing": {
                "live_equities": {
                    "active_candidates": [
                        name
                        for name, ready in (("tradier", tradier_ready), ("alpaca", alpaca_live_ready), ("schwab", schwab_ready))
                        if ready
                    ],
                    "selection_method": (
                        "weighted_round_robin"
                        if settings.broker_equity_live_policy.strip().lower() != "tradier_primary"
                        else "tradier_primary"
                    ),
                    "constraint": "Schwab participates only when a connected user context is available.",
                },
                "options": {
                    "active_candidates": option_candidates,
                    "selection_method": "weighted_round_robin" if len(option_candidates) > 1 else (option_candidates[0] if option_candidates else "none"),
                    "constraint": "Tradier remains the path for advanced multi-leg options; Schwab currently supports direct single-order option submission.",
                },
                "crypto": {
                    "active_candidates": [
                        name
                        for name, ready in (("coinbase", coinbase_ready), ("alpaca", alpaca_live_ready))
                        if ready
                    ],
                    "selection_method": "coinbase_allowlist_then_weighted_round_robin",
                },
            },
        }

    def classify_asset_type(self, symbol: str) -> str:
        upper = symbol.upper()
        if upper.endswith("USD") and len(upper) <= 10:
            return "crypto"
        return "equity"

    def route_broker(
        self,
        *,
        symbol: str,
        liquidity_score: float = 1.0,
        mode: str | None = None,
        asset_class: str | None = None,
        user_id: str | None = None,
    ) -> str:
        del liquidity_score
        asset_type = asset_class or self.classify_asset_type(symbol)
        if asset_type == "crypto":
            upper = symbol.upper()
            normalized = f"{upper[:-3]}-USD" if upper.endswith("USD") and len(upper) > 3 else upper
            allowlist = {item.strip().upper() for item in settings.coinbase_trade_products.split(",") if item.strip()}
            coinbase_ready = bool(
                settings.coinbase_live_trading_enabled
                and settings.coinbase_api_key_name
                and settings.coinbase_api_private_key
            )
            alpaca_ready = bool(settings.alpaca_api_key and settings.alpaca_secret_key)

            if mode == "LIVE_TRADING":
                if normalized in allowlist and coinbase_ready:
                    return "coinbase"

                candidates: list[str] = []
                if coinbase_ready:
                    candidates.append("coinbase")
                if alpaca_ready and not settings.alpaca_paper:
                    candidates.append("alpaca")
                if candidates:
                    return self._weighted_round_robin(
                        bucket="live_crypto",
                        candidates=candidates,
                        weights=self._parse_weight_spec(settings.broker_crypto_live_weights),
                    )

            if normalized in allowlist and coinbase_ready:
                return "coinbase"
            return "alpaca"

        tradier_ready = bool(
            settings.tradier_live_trading_enabled
            and settings.tradier_effective_api_key
            and settings.tradier_effective_account_number
        )
        alpaca_ready = bool(
            settings.alpaca_api_key
            and settings.alpaca_secret_key
            and not settings.alpaca_paper
        )
        schwab_ready = bool(user_id and schwab_client.is_connected(user_id=user_id))

        if asset_type == "option":
            candidates = [name for name, ready in (("tradier", tradier_ready), ("schwab", schwab_ready)) if ready]
            if candidates:
                return self._weighted_round_robin(
                    bucket="live_option",
                    candidates=candidates,
                    weights=self._parse_weight_spec(settings.broker_option_live_weights),
                )
            return "tradier"

        if mode == "LIVE_TRADING":
            candidates: list[str] = []
            if tradier_ready:
                candidates.append("tradier")
            if alpaca_ready:
                candidates.append("alpaca")
            if schwab_ready:
                candidates.append("schwab")
            if candidates:
                if settings.broker_equity_live_policy.strip().lower() == "tradier_primary":
                    return "tradier" if tradier_ready else candidates[0]
                return self._weighted_round_robin(
                    bucket="live_equity",
                    candidates=candidates,
                    weights=self._parse_weight_spec(settings.broker_equity_live_weights),
                )

        return "alpaca"

    def submit(
        self,
        *,
        request: BrokerOrderRequest,
        liquidity_score: float = 1.0,
        mode: str | None = None,
    ) -> BrokerOrderResult:
        broker_name = self.route_broker(
            symbol=request.symbol,
            liquidity_score=liquidity_score,
            mode=mode,
            asset_class=request.asset_class,
            user_id=request.user_id,
        )
        adapter = self._adapters[broker_name]
        return adapter.submit_order(request)


broker_router = BrokerRouter()
