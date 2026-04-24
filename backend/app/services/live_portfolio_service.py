from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

import httpx

from app.core.config import settings
from app.services.alpaca_client import alpaca_client


class LivePortfolioService:
    def _to_float(self, value: object, default: float = 0.0) -> float:
        if value is None:
            return default

        if isinstance(value, (int, float)):
            return float(value)

        if isinstance(value, str):
            text = value.strip().replace(",", "")
            if not text:
                return default
            try:
                return float(text)
            except ValueError:
                return default

        if isinstance(value, dict):
            for key in (
                "value",
                "amount",
                "cash",
                "cash_available",
                "stock_buying_power",
                "option_buying_power",
                "equity",
                "total_equity",
            ):
                if key in value:
                    return self._to_float(value.get(key), default)

            if len(value) == 1:
                return self._to_float(next(iter(value.values())), default)

        return default

    def _extract_tradier_balances_block(self, payload: object) -> dict:
        if not isinstance(payload, dict):
            return {}

        balances = payload.get("balances", {})
        if not isinstance(balances, dict):
            return {}

        for nested_key in ("balance", "account"):
            nested = balances.get(nested_key)
            if isinstance(nested, dict):
                return nested

        return balances

    def snapshot(self) -> dict | None:
        # Prefer Tradier as the source of truth when configured (it is the primary execution broker).
        tradier_snapshot = self._tradier_primary_snapshot()
        if tradier_snapshot is not None:
            return tradier_snapshot

        # Try Schwab next if OAuth token is present.
        schwab_snapshot = self._schwab_primary_snapshot()
        if schwab_snapshot is not None:
            return schwab_snapshot

        # Fall back to Alpaca when neither Tradier nor Schwab is configured.
        account = self._safe_alpaca_account_current()
        positions = self._safe_alpaca_positions_current()
        broker_accounts = self._broker_account_snapshots()

        if account is None and positions is None and not broker_accounts:
            return None

        position_rows = positions if isinstance(positions, list) else ([positions] if positions else [])
        active_positions: list[dict] = []
        sector_counter: Counter[str] = Counter()
        strategy_counter: Counter[str] = Counter()
        total_exposure = 0.0

        for position in position_rows:
            symbol = str(position.get("symbol", "")).upper()
            qty = float(position.get("qty") or 0.0)
            market_value = abs(float(position.get("market_value") or 0.0))
            if not symbol or qty == 0:
                continue
            side = "LONG" if qty > 0 else "SHORT"
            strategy = "LIVE_ALPACA"
            sector = self._sector_for_symbol(symbol)
            total_exposure += market_value
            sector_counter[sector] += market_value
            strategy_counter[strategy] += market_value
            entry_price = float(position.get("avg_entry_price") or 0.0)
            current_price = float(position.get("current_price") or entry_price)
            unrealized_pnl = float(position.get("unrealized_pl") or 0.0)
            cost_basis = entry_price * abs(qty)
            unrealized_pnl_pct = (unrealized_pnl / cost_basis) if cost_basis > 0 else 0.0
            active_positions.append(
                {
                    "symbol": symbol,
                    "strategy": strategy,
                    "side": side,
                    "entry_price": entry_price,
                    "current_price": current_price,
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "unrealized_pnl_pct": round(unrealized_pnl_pct, 4),
                    "units": abs(qty),
                    "notional": market_value,
                    "sector": sector,
                    "opened_at": datetime.now(tz=timezone.utc),
                }
            )

        if account is not None:
            balance = float(account.get("equity") or account.get("cash") or 0.0)
            buying_power = float(account.get("buying_power") or 0.0)
        else:
            balance = sum(
                float(item.get("account_balance") or 0.0)
                for item in broker_accounts
                if item.get("account_balance") is not None
            )
            buying_power = sum(
                float(item.get("buying_power") or 0.0)
                for item in broker_accounts
                if item.get("buying_power") is not None
            )

        return {
            "account_balance": round(balance, 2),
            "active_positions": active_positions,
            "total_exposure": round(total_exposure, 2),
            "risk_exposure_pct": round((total_exposure / balance) if balance > 0 else 0.0, 4),
            "sector_concentration": {k: round(v, 2) for k, v in sector_counter.items()},
            "strategy_exposure": {k: round(v, 2) for k, v in strategy_counter.items()},
            "available_buying_power": round(buying_power, 2),
            "max_concurrent_trades": 12,
            "broker_accounts": broker_accounts,
        }

    # ------------------------------------------------------------------
    # Tradier-primary portfolio: positions + balances from broker source
    # ------------------------------------------------------------------

    def _tradier_primary_snapshot(self) -> dict | None:
        """Return a portfolio snapshot sourced entirely from Tradier when configured.

        This is the preferred data path when Tradier is the active execution
        broker.  Falls back to None if Tradier credentials are absent, so the
        caller can try Alpaca instead.
        """
        from app.core.config import settings as _s  # avoid circular at module level

        if not _s.tradier_effective_api_key or not _s.tradier_effective_account_number:
            return None

        balances = self._tradier_balances()
        if balances is None:
            return None

        positions = self._tradier_positions()
        broker_accounts = self._broker_account_snapshots()

        active_positions: list[dict] = []
        sector_counter: Counter[str] = Counter()
        strategy_counter: Counter[str] = Counter()
        total_exposure = 0.0

        for pos in positions:
            symbol = str(pos.get("symbol", "")).upper()
            qty = float(pos.get("quantity") or 0.0)
            if not symbol or qty == 0:
                continue
            cost_basis = float(pos.get("cost_basis") or 0.0)
            entry_price = round(cost_basis / abs(qty), 4) if abs(qty) > 0 else 0.0
            # Tradier positions don't carry real-time price; use cost basis as best estimate.
            # The sync service will enrich this with live quotes.
            current_price = float(pos.get("current_price") or entry_price)
            market_value = current_price * abs(qty)
            unrealized_pnl = (current_price - entry_price) * abs(qty) if qty > 0 else (entry_price - current_price) * abs(qty)
            unrealized_pnl_pct = (unrealized_pnl / cost_basis) if cost_basis > 0 else 0.0
            side = "LONG" if qty > 0 else "SHORT"
            sector = self._sector_for_symbol(symbol)
            total_exposure += market_value
            sector_counter[sector] += market_value
            strategy_counter["LIVE_TRADIER"] += market_value
            active_positions.append(
                {
                    "symbol": symbol,
                    "strategy": "LIVE_TRADIER",
                    "side": side,
                    "entry_price": round(entry_price, 4),
                    "current_price": round(current_price, 4),
                    "unrealized_pnl": round(unrealized_pnl, 2),
                    "unrealized_pnl_pct": round(unrealized_pnl_pct, 4),
                    "units": abs(qty),
                    "notional": round(market_value, 2),
                    "sector": sector,
                    "opened_at": pos.get("date_acquired") or datetime.now(tz=timezone.utc),
                    "tradier_position_id": pos.get("id"),
                    "source": "tradier",
                }
            )

        margin_block = balances.get("margin", {}) if isinstance(balances, dict) else {}
        if not isinstance(margin_block, dict):
            margin_block = {}

        balance = self._to_float(
            balances.get("total_equity")
            or balances.get("equity")
            or balances.get("cash")
            or balances.get("cash_available"),
            0.0,
        )
        buying_power = self._to_float(
            margin_block.get("stock_buying_power")
            or balances.get("cash_available")
            or balances.get("cash"),
            0.0,
        )

        return {
            "account_balance": round(balance, 2),
            "active_positions": active_positions,
            "total_exposure": round(total_exposure, 2),
            "risk_exposure_pct": round((total_exposure / balance) if balance > 0 else 0.0, 4),
            "sector_concentration": {k: round(v, 2) for k, v in sector_counter.items()},
            "strategy_exposure": {k: round(v, 2) for k, v in strategy_counter.items()},
            "available_buying_power": round(buying_power, 2),
            "max_concurrent_trades": 12,
            "broker_accounts": broker_accounts,
            "data_source": "tradier",
        }

    def _tradier_balances(self) -> dict | None:
        """Fetch raw Tradier account balances dict. Returns None on failure."""
        from app.core.config import settings as _s
        from app.services.tradier_client import tradier_client as _tc

        try:
            payload = _tc.get(f"/accounts/{_s.tradier_effective_account_number}/balances")
            bal = self._extract_tradier_balances_block(payload)
            if not bal:
                return None
            # Normalise margin block for convenient access
            margin = bal.get("margin", {}) or {}
            if not isinstance(margin, dict):
                margin = {}
            return {
                "total_equity": self._to_float(
                    bal.get("total_equity")
                    or bal.get("equity")
                    or bal.get("cash")
                    or bal.get("cash_available"),
                    0.0,
                ),
                "cash": self._to_float(bal.get("cash"), 0.0),
                "cash_available": self._to_float(
                    bal.get("cash_available") or margin.get("stock_buying_power") or bal.get("cash"),
                    0.0,
                ),
                "margin": margin,
                "option_buying_power": self._to_float(margin.get("option_buying_power"), 0.0),
                "raw": bal,
            }
        except Exception:
            return None

    def _tradier_positions(self) -> list[dict]:
        """Fetch live positions from Tradier. Returns empty list on failure."""
        from app.core.config import settings as _s
        from app.services.tradier_client import tradier_client as _tc

        try:
            payload = _tc.get(f"/accounts/{_s.tradier_effective_account_number}/positions")
            positions_block = (payload or {}).get("positions", {})
            if not positions_block or positions_block == "null":
                return []
            raw = positions_block.get("position", [])
            if isinstance(raw, dict):
                raw = [raw]
            return raw if isinstance(raw, list) else []
        except Exception:
            return []

    # ------------------------------------------------------------------

    def _safe_alpaca_account_current(self) -> dict | None:
        try:
            return alpaca_client.get("/v2/account")
        except Exception:
            return None

    def _safe_alpaca_positions_current(self) -> list[dict] | None:
        try:
            payload = alpaca_client.get("/v2/positions")
            if isinstance(payload, list):
                return payload
            if isinstance(payload, dict):
                return [payload]
        except Exception:
            return None
        return None

    def _broker_account_snapshots(self) -> list[dict]:
        rows: list[dict] = []

        rows.append(self._alpaca_snapshot_for_mode(paper=True))
        rows.append(self._alpaca_snapshot_for_mode(paper=False))

        coinbase = self._coinbase_snapshot()
        if coinbase is not None:
            rows.append(coinbase)

        tradier = self._tradier_snapshot()
        if tradier is not None:
            rows.append(tradier)

        schwab = self._schwab_account_snapshot()
        if schwab is not None:
            rows.append(schwab)

        return rows

    def _alpaca_snapshot_for_mode(self, *, paper: bool) -> dict:
        mode = "paper" if paper else "live"
        base_url = "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"

        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            return {
                "broker": "alpaca",
                "account_label": f"Alpaca {mode.title()}",
                "account_mode": mode,
                "connected": False,
                "account_balance": None,
                "buying_power": None,
                "currency": "USD",
                "last_error": "Missing ALPACA_API_KEY or ALPACA_SECRET_KEY",
            }

        headers = {
            "APCA-API-KEY-ID": settings.alpaca_api_key,
            "APCA-API-SECRET-KEY": settings.alpaca_secret_key,
        }
        try:
            with httpx.Client(timeout=8) as client:
                resp = client.get(f"{base_url}/v2/account", headers=headers)
            resp.raise_for_status()
            payload = resp.json()
            return {
                "broker": "alpaca",
                "account_label": f"Alpaca {mode.title()}",
                "account_mode": mode,
                "connected": True,
                "account_balance": float(payload.get("equity") or payload.get("cash") or 0.0),
                "buying_power": float(payload.get("buying_power") or 0.0),
                "currency": "USD",
                "last_error": None,
            }
        except Exception as exc:
            if isinstance(exc, httpx.HTTPStatusError):
                status = exc.response.status_code
                if status == 401:
                    message = f"Unauthorized (401): verify Alpaca {mode} API key/secret for this mode."
                else:
                    message = f"Alpaca {mode.title()} account request failed (HTTP {status})."
            else:
                message = str(exc)
            return {
                "broker": "alpaca",
                "account_label": f"Alpaca {mode.title()}",
                "account_mode": mode,
                "connected": False,
                "account_balance": None,
                "buying_power": None,
                "currency": "USD",
                "last_error": message,
            }

    def _coinbase_snapshot(self) -> dict | None:
        if not settings.coinbase_api_key_name or not settings.coinbase_api_private_key:
            return {
                "broker": "coinbase",
                "account_label": "Coinbase Live",
                "account_mode": "live",
                "connected": False,
                "account_balance": None,
                "buying_power": None,
                "currency": "USD",
                "last_error": "Missing COINBASE_API_KEY_NAME or COINBASE_API_PRIVATE_KEY",
            }

        try:
            from coinbase.rest import RESTClient

            client = RESTClient(
                api_key=settings.coinbase_api_key_name,
                api_secret=settings.coinbase_api_private_key,
                timeout=8,
            )
            payload = client.get_accounts(limit=250)
            data = payload.to_dict() if hasattr(payload, "to_dict") else payload
            accounts = data.get("accounts", []) if isinstance(data, dict) else []

            usd_like = 0.0
            for account in accounts:
                row = account.to_dict() if hasattr(account, "to_dict") else account
                if not isinstance(row, dict):
                    continue
                currency = str(row.get("currency") or "").upper()
                available = row.get("available_balance")
                if isinstance(available, dict):
                    value = float(available.get("value") or 0.0)
                else:
                    value = float(available or 0.0)
                if currency in {"USD", "USDC"}:
                    usd_like += value

            return {
                "broker": "coinbase",
                "account_label": "Coinbase Live",
                "account_mode": "live",
                "connected": True,
                "account_balance": usd_like,
                "buying_power": usd_like,
                "currency": "USD",
                "last_error": None,
            }
        except Exception as exc:
            return {
                "broker": "coinbase",
                "account_label": "Coinbase Live",
                "account_mode": "live",
                "connected": False,
                "account_balance": None,
                "buying_power": None,
                "currency": "USD",
                "last_error": str(exc),
            }

    def _tradier_snapshot(self) -> dict | None:
        base_url = settings.tradier_base_url.rstrip("/") if settings.tradier_base_url else (
            "https://sandbox.tradier.com/v1" if settings.tradier_sandbox else "https://api.tradier.com/v1"
        )
        mode = "sandbox" if settings.tradier_sandbox else "live"

        if not settings.tradier_effective_api_key or not settings.tradier_effective_account_number:
            return {
                "broker": "tradier",
                "account_label": f"Tradier {mode.title()}",
                "account_mode": mode,
                "connected": False,
                "account_balance": None,
                "buying_power": None,
                "currency": "USD",
                "last_error": "Missing active Tradier key/account for current TRADIER_SANDBOX mode",
            }

        headers = {
            "Authorization": f"Bearer {settings.tradier_effective_api_key}",
            "Accept": "application/json",
        }
        endpoint = f"{base_url}/accounts/{settings.tradier_effective_account_number}/balances"
        try:
            with httpx.Client(timeout=8) as client:
                resp = client.get(endpoint, headers=headers)
            resp.raise_for_status()
            payload = resp.json() if resp.content else {}
            balances = self._extract_tradier_balances_block(payload)
            margin_block = balances.get("margin") if isinstance(balances, dict) else {}
            if not isinstance(margin_block, dict):
                margin_block = {}
            total_equity = self._to_float(
                balances.get("total_equity")
                or balances.get("equity")
                or balances.get("cash")
                or balances.get("cash_available"),
                0.0,
            )
            buying_power = self._to_float(
                margin_block.get("stock_buying_power")
                or balances.get("cash_available")
                or balances.get("cash"),
                0.0,
            )
            return {
                "broker": "tradier",
                "account_label": f"Tradier {mode.title()}",
                "account_mode": mode,
                "connected": True,
                "account_balance": total_equity,
                "buying_power": buying_power,
                "currency": "USD",
                "last_error": None,
            }
        except Exception as exc:
            return {
                "broker": "tradier",
                "account_label": f"Tradier {mode.title()}",
                "account_mode": mode,
                "connected": False,
                "account_balance": None,
                "buying_power": None,
                "currency": "USD",
                "last_error": str(exc),
            }

    # ------------------------------------------------------------------
    # Schwab
    # ------------------------------------------------------------------

    def _schwab_primary_snapshot(self) -> dict | None:
        """Return a full portfolio snapshot from Schwab OAuth account, or None."""
        try:
            from app.services.schwab_client import schwab_client
        except ImportError:
            return None

        if not schwab_client.is_connected():
            return None

        snap = schwab_client.portfolio_snapshot()
        if not snap:
            return None

        broker_accounts = self._broker_account_snapshots()
        positions = snap.get("positions", [])
        balance = snap.get("account_balance", 0.0)
        buying_power = snap.get("buying_power", 0.0)
        total_exposure = sum(float(p.get("notional") or 0.0) for p in positions)

        sector_counter: Counter[str] = Counter()
        strategy_counter: Counter[str] = Counter()
        for p in positions:
            sector_counter[p.get("sector", "OTHER")] += float(p.get("notional") or 0.0)
            strategy_counter["LIVE_SCHWAB"] += float(p.get("notional") or 0.0)

        return {
            "account_balance": round(balance, 2),
            "active_positions": positions,
            "total_exposure": round(total_exposure, 2),
            "risk_exposure_pct": round((total_exposure / balance) if balance > 0 else 0.0, 4),
            "sector_concentration": {k: round(v, 2) for k, v in sector_counter.items()},
            "strategy_exposure": {k: round(v, 2) for k, v in strategy_counter.items()},
            "available_buying_power": round(buying_power, 2),
            "max_concurrent_trades": 12,
            "broker_accounts": broker_accounts,
            "data_source": "schwab",
        }

    def _schwab_account_snapshot(self) -> dict | None:
        """Return a BrokerAccountSnapshot-compatible dict for Schwab, or None."""
        try:
            from app.services.schwab_client import schwab_client
        except ImportError:
            return None

        if not schwab_client.is_connected():
            return {
                "broker": "schwab",
                "account_label": "Charles Schwab",
                "account_mode": "live",
                "connected": False,
                "account_balance": None,
                "buying_power": None,
                "currency": "USD",
                "last_error": "No active Schwab OAuth connection",
            }

        snap = schwab_client.portfolio_snapshot()
        if not snap:
            return {
                "broker": "schwab",
                "account_label": "Charles Schwab",
                "account_mode": "live",
                "connected": False,
                "account_balance": None,
                "buying_power": None,
                "currency": "USD",
                "last_error": "Schwab connected but account data unavailable",
            }

        label = ", ".join(snap.get("account_labels", ["Charles Schwab"])) or "Charles Schwab"
        return {
            "broker": "schwab",
            "account_label": label,
            "account_mode": "live",
            "connected": True,
            "account_balance": snap.get("account_balance"),
            "buying_power": snap.get("buying_power"),
            "currency": "USD",
            "last_error": None,
        }

    def _sector_for_symbol(self, symbol: str) -> str:
        mapping = {
            "AAPL": "TECH",
            "MSFT": "TECH",
            "NVDA": "TECH",
            "AMD": "TECH",
            "TSLA": "AUTO",
            "SPY": "INDEX",
        }
        return mapping.get(symbol.upper(), "OTHER")


live_portfolio_service = LivePortfolioService()
