from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.config import settings
from app.services.agent_manager import agent_manager
from app.services.capital_allocator import AllocationInput, capital_allocator
from app.services.consensus_engine import consensus_engine
from app.services.compounding_engine import compounding_engine
from app.services.context_intelligence import context_intelligence
from app.services.brokers.router import broker_router
from app.services.swarm.execution_bridge import execution_bridge
from app.services.explainability import build_explainability
from app.services.historical_data_service import historical_data_service
from app.services.kronos_service import kronos_service
from app.services.mission_policy_engine import mission_policy_engine
from app.services.news.news_intelligence import news_intelligence
from app.services.options_service import options_service
from app.services.opportunity_persistence_store import opportunity_persistence_store
from app.services.regime_detector import regime_detector
from app.services.risk_engine import risk_engine
from app.services.scan_health import logger
from app.services.signal_engine import signal_engine
from app.services.execution_quality_engine import execution_quality_engine
from app.services.live_experiment_promotion_service import live_experiment_promotion_service
from app.services.meta_risk_governor import meta_risk_governor
from app.services.system_mode_service import system_mode_service
from app.services.strategy_evolution_service import strategy_evolution_service


@dataclass
class UniverseTicker:
    symbol: str
    asset_class: str
    region: str


UNIVERSE: list[UniverseTicker] = [
    # ── Mag-7 / Mega Cap Tech ──────────────────────────────────────────────────
    UniverseTicker("AAPL", "equity", "US"),
    UniverseTicker("MSFT", "equity", "US"),
    UniverseTicker("NVDA", "equity", "US"),
    UniverseTicker("AMZN", "equity", "US"),
    UniverseTicker("GOOGL", "equity", "US"),
    UniverseTicker("GOOG", "equity", "US"),
    UniverseTicker("META", "equity", "US"),
    UniverseTicker("TSLA", "equity", "US"),
    UniverseTicker("ORCL", "equity", "US"),
    UniverseTicker("INTC", "equity", "US"),
    UniverseTicker("CSCO", "equity", "US"),
    UniverseTicker("CRM", "equity", "US"),
    UniverseTicker("SNOW", "equity", "US"),
    UniverseTicker("PLTR", "equity", "US"),
    UniverseTicker("ADBE", "equity", "US"),
    UniverseTicker("NOW", "equity", "US"),
    UniverseTicker("INTU", "equity", "US"),
    UniverseTicker("PANW", "equity", "US"),
    UniverseTicker("CRWD", "equity", "US"),
    UniverseTicker("ZS", "equity", "US"),
    UniverseTicker("DDOG", "equity", "US"),
    UniverseTicker("MDB", "equity", "US"),
    UniverseTicker("NET", "equity", "US"),
    UniverseTicker("TEAM", "equity", "US"),
    UniverseTicker("OKTA", "equity", "US"),
    UniverseTicker("HUBS", "equity", "US"),
    UniverseTicker("TWLO", "equity", "US"),
    UniverseTicker("SHOP", "equity", "US"),
    UniverseTicker("U", "equity", "US"),
    UniverseTicker("RBLX", "equity", "US"),
    UniverseTicker("COIN", "equity", "US"),
    UniverseTicker("HOOD", "equity", "US"),
    UniverseTicker("MSTR", "equity", "US"),
    UniverseTicker("ANET", "equity", "US"),
    UniverseTicker("SMCI", "equity", "US"),
    UniverseTicker("ARM", "equity", "US"),
    UniverseTicker("ASML", "equity", "EU"),
    UniverseTicker("TSM", "equity", "TW"),
    UniverseTicker("AVGO", "equity", "US"),
    UniverseTicker("QCOM", "equity", "US"),
    UniverseTicker("AMD", "equity", "US"),
    UniverseTicker("MRVL", "equity", "US"),
    UniverseTicker("KLAC", "equity", "US"),
    UniverseTicker("LRCX", "equity", "US"),
    UniverseTicker("AMAT", "equity", "US"),
    UniverseTicker("MCHP", "equity", "US"),
    UniverseTicker("TXN", "equity", "US"),
    UniverseTicker("ON", "equity", "US"),
    UniverseTicker("MPWR", "equity", "US"),
    # ── Financials ────────────────────────────────────────────────────────────
    UniverseTicker("JPM", "equity", "US"),
    UniverseTicker("BAC", "equity", "US"),
    UniverseTicker("WFC", "equity", "US"),
    UniverseTicker("GS", "equity", "US"),
    UniverseTicker("MS", "equity", "US"),
    UniverseTicker("C", "equity", "US"),
    UniverseTicker("USB", "equity", "US"),
    UniverseTicker("PNC", "equity", "US"),
    UniverseTicker("TFC", "equity", "US"),
    UniverseTicker("SCHW", "equity", "US"),
    UniverseTicker("AXP", "equity", "US"),
    UniverseTicker("V", "equity", "US"),
    UniverseTicker("MA", "equity", "US"),
    UniverseTicker("PYPL", "equity", "US"),
    UniverseTicker("SQ", "equity", "US"),
    UniverseTicker("FI", "equity", "US"),
    UniverseTicker("FIS", "equity", "US"),
    UniverseTicker("ICE", "equity", "US"),
    UniverseTicker("CME", "equity", "US"),
    UniverseTicker("SPGI", "equity", "US"),
    UniverseTicker("MCO", "equity", "US"),
    UniverseTicker("BLK", "equity", "US"),
    UniverseTicker("KKR", "equity", "US"),
    UniverseTicker("APO", "equity", "US"),
    UniverseTicker("BX", "equity", "US"),
    UniverseTicker("ARES", "equity", "US"),
    # ── Healthcare / Biotech ──────────────────────────────────────────────────
    UniverseTicker("UNH", "equity", "US"),
    UniverseTicker("LLY", "equity", "US"),
    UniverseTicker("JNJ", "equity", "US"),
    UniverseTicker("PFE", "equity", "US"),
    UniverseTicker("MRK", "equity", "US"),
    UniverseTicker("ABBV", "equity", "US"),
    UniverseTicker("BMY", "equity", "US"),
    UniverseTicker("AMGN", "equity", "US"),
    UniverseTicker("GILD", "equity", "US"),
    UniverseTicker("BIIB", "equity", "US"),
    UniverseTicker("REGN", "equity", "US"),
    UniverseTicker("VRTX", "equity", "US"),
    UniverseTicker("MRNA", "equity", "US"),
    UniverseTicker("ISRG", "equity", "US"),
    UniverseTicker("MDT", "equity", "US"),
    UniverseTicker("BSX", "equity", "US"),
    UniverseTicker("ZBH", "equity", "US"),
    UniverseTicker("CVS", "equity", "US"),
    UniverseTicker("CI", "equity", "US"),
    UniverseTicker("HUM", "equity", "US"),
    UniverseTicker("DXCM", "equity", "US"),
    UniverseTicker("IDXX", "equity", "US"),
    UniverseTicker("ILMN", "equity", "US"),
    UniverseTicker("IQV", "equity", "US"),
    UniverseTicker("TMO", "equity", "US"),
    UniverseTicker("DHR", "equity", "US"),
    UniverseTicker("A", "equity", "US"),
    UniverseTicker("HZNP", "equity", "US"),
    UniverseTicker("SGEN", "equity", "US"),
    UniverseTicker("ALNY", "equity", "US"),
    # ── Consumer Staples / Discretionary ─────────────────────────────────────
    UniverseTicker("KO", "equity", "US"),
    UniverseTicker("PEP", "equity", "US"),
    UniverseTicker("PG", "equity", "US"),
    UniverseTicker("WMT", "equity", "US"),
    UniverseTicker("COST", "equity", "US"),
    UniverseTicker("HD", "equity", "US"),
    UniverseTicker("LOW", "equity", "US"),
    UniverseTicker("MCD", "equity", "US"),
    UniverseTicker("SBUX", "equity", "US"),
    UniverseTicker("YUM", "equity", "US"),
    UniverseTicker("NKE", "equity", "US"),
    UniverseTicker("TGT", "equity", "US"),
    UniverseTicker("DLTR", "equity", "US"),
    UniverseTicker("DG", "equity", "US"),
    UniverseTicker("KR", "equity", "US"),
    UniverseTicker("CLX", "equity", "US"),
    UniverseTicker("CL", "equity", "US"),
    UniverseTicker("KMB", "equity", "US"),
    UniverseTicker("GIS", "equity", "US"),
    UniverseTicker("K", "equity", "US"),
    UniverseTicker("HSY", "equity", "US"),
    UniverseTicker("MO", "equity", "US"),
    UniverseTicker("PM", "equity", "US"),
    UniverseTicker("EL", "equity", "US"),
    UniverseTicker("ULTA", "equity", "US"),
    UniverseTicker("LULU", "equity", "US"),
    UniverseTicker("DECK", "equity", "US"),
    UniverseTicker("CHWY", "equity", "US"),
    UniverseTicker("EBAY", "equity", "US"),
    UniverseTicker("W", "equity", "US"),
    UniverseTicker("ETSY", "equity", "US"),
    # ── Energy ───────────────────────────────────────────────────────────────
    UniverseTicker("XOM", "equity", "US"),
    UniverseTicker("CVX", "equity", "US"),
    UniverseTicker("COP", "equity", "US"),
    UniverseTicker("SLB", "equity", "US"),
    UniverseTicker("EOG", "equity", "US"),
    UniverseTicker("PXD", "equity", "US"),
    UniverseTicker("DVN", "equity", "US"),
    UniverseTicker("MPC", "equity", "US"),
    UniverseTicker("VLO", "equity", "US"),
    UniverseTicker("PSX", "equity", "US"),
    UniverseTicker("HAL", "equity", "US"),
    UniverseTicker("BKR", "equity", "US"),
    UniverseTicker("OXY", "equity", "US"),
    UniverseTicker("KMI", "equity", "US"),
    UniverseTicker("WMB", "equity", "US"),
    UniverseTicker("ET", "equity", "US"),
    UniverseTicker("ENPH", "equity", "US"),
    UniverseTicker("FSLR", "equity", "US"),
    UniverseTicker("NEE", "equity", "US"),
    UniverseTicker("CEG", "equity", "US"),
    # ── Industrials / Defense ─────────────────────────────────────────────────
    UniverseTicker("BA", "equity", "US"),
    UniverseTicker("CAT", "equity", "US"),
    UniverseTicker("DE", "equity", "US"),
    UniverseTicker("GE", "equity", "US"),
    UniverseTicker("RTX", "equity", "US"),
    UniverseTicker("LMT", "equity", "US"),
    UniverseTicker("NOC", "equity", "US"),
    UniverseTicker("GD", "equity", "US"),
    UniverseTicker("LHX", "equity", "US"),
    UniverseTicker("HII", "equity", "US"),
    UniverseTicker("MMM", "equity", "US"),
    UniverseTicker("HON", "equity", "US"),
    UniverseTicker("EMR", "equity", "US"),
    UniverseTicker("ETN", "equity", "US"),
    UniverseTicker("ROK", "equity", "US"),
    UniverseTicker("PH", "equity", "US"),
    UniverseTicker("IR", "equity", "US"),
    UniverseTicker("CMI", "equity", "US"),
    UniverseTicker("PCAR", "equity", "US"),
    UniverseTicker("FDX", "equity", "US"),
    UniverseTicker("UPS", "equity", "US"),
    UniverseTicker("DAL", "equity", "US"),
    UniverseTicker("UAL", "equity", "US"),
    UniverseTicker("AAL", "equity", "US"),
    UniverseTicker("LUV", "equity", "US"),
    # ── Telecom / Media ───────────────────────────────────────────────────────
    UniverseTicker("T", "equity", "US"),
    UniverseTicker("VZ", "equity", "US"),
    UniverseTicker("TMUS", "equity", "US"),
    UniverseTicker("NFLX", "equity", "US"),
    UniverseTicker("DIS", "equity", "US"),
    UniverseTicker("WBD", "equity", "US"),
    UniverseTicker("PARA", "equity", "US"),
    UniverseTicker("FOX", "equity", "US"),
    UniverseTicker("CHTR", "equity", "US"),
    UniverseTicker("CMCSA", "equity", "US"),
    # ── REITs ─────────────────────────────────────────────────────────────────
    UniverseTicker("AMT", "equity", "US"),
    UniverseTicker("PLD", "equity", "US"),
    UniverseTicker("EQIX", "equity", "US"),
    UniverseTicker("CCI", "equity", "US"),
    UniverseTicker("SBAC", "equity", "US"),
    UniverseTicker("PSA", "equity", "US"),
    UniverseTicker("DLR", "equity", "US"),
    UniverseTicker("O", "equity", "US"),
    UniverseTicker("WPC", "equity", "US"),
    UniverseTicker("SPG", "equity", "US"),
    UniverseTicker("EQR", "equity", "US"),
    UniverseTicker("VICI", "equity", "US"),
    # ── International Single-Country ─────────────────────────────────────────
    UniverseTicker("EWJ", "equity", "JP"),
    UniverseTicker("EWU", "equity", "UK"),
    UniverseTicker("EWG", "equity", "DE"),
    UniverseTicker("EWQ", "equity", "FR"),
    UniverseTicker("EWI", "equity", "IT"),
    UniverseTicker("EWP", "equity", "ES"),
    UniverseTicker("EWC", "equity", "CA"),
    UniverseTicker("EWA", "equity", "AU"),
    UniverseTicker("EWZ", "equity", "BR"),
    UniverseTicker("EWY", "equity", "KR"),
    UniverseTicker("EWT", "equity", "TW"),
    UniverseTicker("INDA", "equity", "IN"),
    UniverseTicker("FXI", "equity", "CN"),
    UniverseTicker("KWEB", "equity", "CN"),
    UniverseTicker("EEM", "equity", "EM"),
    UniverseTicker("VWO", "equity", "EM"),
    UniverseTicker("EFA", "equity", "INTL"),
    UniverseTicker("IEFA", "equity", "INTL"),
    UniverseTicker("EZU", "equity", "EU"),
    # ── Broad Market / Sector ETFs ────────────────────────────────────────────
    UniverseTicker("SPY", "etf", "US"),
    UniverseTicker("QQQ", "etf", "US"),
    UniverseTicker("IWM", "etf", "US"),
    UniverseTicker("DIA", "etf", "US"),
    UniverseTicker("IVV", "etf", "US"),
    UniverseTicker("VOO", "etf", "US"),
    UniverseTicker("VTI", "etf", "US"),
    UniverseTicker("VUG", "etf", "US"),
    UniverseTicker("VTV", "etf", "US"),
    UniverseTicker("SPLG", "etf", "US"),
    UniverseTicker("SCHD", "etf", "US"),
    UniverseTicker("DVY", "etf", "US"),
    UniverseTicker("XLF", "etf", "US"),
    UniverseTicker("XLE", "etf", "US"),
    UniverseTicker("XLY", "etf", "US"),
    UniverseTicker("XLV", "etf", "US"),
    UniverseTicker("XLI", "etf", "US"),
    UniverseTicker("XLK", "etf", "US"),
    UniverseTicker("XLB", "etf", "US"),
    UniverseTicker("XLRE", "etf", "US"),
    UniverseTicker("XLU", "etf", "US"),
    UniverseTicker("XLC", "etf", "US"),
    UniverseTicker("XLP", "etf", "US"),
    UniverseTicker("SMH", "etf", "US"),
    UniverseTicker("SOXX", "etf", "US"),
    UniverseTicker("IGV", "etf", "US"),
    UniverseTicker("CIBR", "etf", "US"),
    UniverseTicker("ARKK", "etf", "US"),
    UniverseTicker("ARKG", "etf", "US"),
    UniverseTicker("ARKW", "etf", "US"),
    UniverseTicker("IBB", "etf", "US"),
    UniverseTicker("XBI", "etf", "US"),
    UniverseTicker("JETS", "etf", "US"),
    UniverseTicker("HACK", "etf", "US"),
    UniverseTicker("AIQ", "etf", "US"),
    UniverseTicker("BOTZ", "etf", "US"),
    # ── Fixed Income / Macro ETFs ─────────────────────────────────────────────
    UniverseTicker("TLT", "etf", "US"),
    UniverseTicker("IEF", "etf", "US"),
    UniverseTicker("SHY", "etf", "US"),
    UniverseTicker("HYG", "etf", "US"),
    UniverseTicker("LQD", "etf", "US"),
    UniverseTicker("JNK", "etf", "US"),
    UniverseTicker("BND", "etf", "US"),
    UniverseTicker("AGG", "etf", "US"),
    UniverseTicker("TIPS", "etf", "US"),
    UniverseTicker("EMB", "etf", "US"),
    # ── Commodities ───────────────────────────────────────────────────────────
    UniverseTicker("GLD", "etf", "US"),
    UniverseTicker("IAU", "etf", "US"),
    UniverseTicker("SLV", "etf", "US"),
    UniverseTicker("PPLT", "etf", "US"),
    UniverseTicker("PALL", "etf", "US"),
    UniverseTicker("USO", "etf", "US"),
    UniverseTicker("UNG", "etf", "US"),
    UniverseTicker("CORN", "etf", "US"),
    UniverseTicker("SOYB", "etf", "US"),
    UniverseTicker("WEAT", "etf", "US"),
    UniverseTicker("DBA", "etf", "US"),
    UniverseTicker("PDBC", "etf", "US"),
    UniverseTicker("COPX", "etf", "US"),
    UniverseTicker("REMX", "etf", "US"),
    # ── Volatility / Inverse / Leveraged ─────────────────────────────────────
    UniverseTicker("VXX", "etf", "US"),
    UniverseTicker("UVXY", "etf", "US"),
    UniverseTicker("SVXY", "etf", "US"),
    UniverseTicker("SQQQ", "etf", "US"),
    UniverseTicker("TQQQ", "etf", "US"),
    UniverseTicker("SPXU", "etf", "US"),
    UniverseTicker("SPXL", "etf", "US"),
    UniverseTicker("SOXS", "etf", "US"),
    UniverseTicker("SOXL", "etf", "US"),
    # ── Crypto ───────────────────────────────────────────────────────────────
    UniverseTicker("BTCUSD", "crypto", "GLOBAL"),
    UniverseTicker("ETHUSD", "crypto", "GLOBAL"),
    UniverseTicker("SOLUSD", "crypto", "GLOBAL"),
    UniverseTicker("ADAUSD", "crypto", "GLOBAL"),
    UniverseTicker("DOGEUSD", "crypto", "GLOBAL"),
    UniverseTicker("XRPUSD", "crypto", "GLOBAL"),
    UniverseTicker("DOTUSD", "crypto", "GLOBAL"),
    UniverseTicker("AVAXUSD", "crypto", "GLOBAL"),
    UniverseTicker("MATICUSD", "crypto", "GLOBAL"),
    UniverseTicker("LTCUSD", "crypto", "GLOBAL"),
    UniverseTicker("LINKUSD", "crypto", "GLOBAL"),
    UniverseTicker("UNIUSD", "crypto", "GLOBAL"),
    UniverseTicker("ATOMUSD", "crypto", "GLOBAL"),
    UniverseTicker("NEARUSD", "crypto", "GLOBAL"),
    UniverseTicker("APTUSD", "crypto", "GLOBAL"),
    UniverseTicker("ARBUSD", "crypto", "GLOBAL"),
    UniverseTicker("OPUSD", "crypto", "GLOBAL"),
    UniverseTicker("INJUSD", "crypto", "GLOBAL"),
    UniverseTicker("SUIUSD", "crypto", "GLOBAL"),
    UniverseTicker("SEIUSD", "crypto", "GLOBAL"),
    UniverseTicker("BNBUSD", "crypto", "GLOBAL"),
    UniverseTicker("TRXUSD", "crypto", "GLOBAL"),
    UniverseTicker("TONUSD", "crypto", "GLOBAL"),
    UniverseTicker("PEPEUSD", "crypto", "GLOBAL"),
    UniverseTicker("WIFUSD", "crypto", "GLOBAL"),
    UniverseTicker("BONKUSD", "crypto", "GLOBAL"),
    UniverseTicker("FLOKIUSD", "crypto", "GLOBAL"),
    UniverseTicker("RENDERUSD", "crypto", "GLOBAL"),
    UniverseTicker("FETHUSD", "crypto", "GLOBAL"),
    UniverseTicker("WLDUSD", "crypto", "GLOBAL"),
]

DEFAULT_HIGH_RISK_SPRINT_SYMBOLS: tuple[str, ...] = (
    "SOUN",
    "ACHR",
    "JOBY",
    "OPEN",
    "LCID",
    "PLUG",
    "DNA",
    "SOFI",
    "RKLB",
    "HUT",
    "RIOT",
    "IREN",
)


class OpportunityScanner:
    @staticmethod
    def _bucket_for(item: dict) -> str:
        if item.get("scan_mode") == "high_risk_sprint":
            return "high_risk_sprint"
        if item.get("asset_class") == "crypto":
            return "crypto_momentum"
        if item.get("regime") == "RANGE_BOUND":
            return "mean_reversion"
        return "core_trend"

    def _high_risk_sprint_active(self, *, goal_pressure_multiplier: float) -> bool:
        if settings.high_risk_sprint_mode_enabled:
            return True
        if not settings.high_risk_sprint_auto_enabled:
            return False
        return goal_pressure_multiplier >= settings.high_risk_sprint_auto_trigger_pressure

    def _coinbase_priority_symbols(self) -> set[str]:
        symbols: set[str] = set()
        for product in settings.coinbase_trade_products.split(","):
            cleaned = product.strip().upper()
            if not cleaned:
                continue
            if "-" in cleaned:
                base, quote = cleaned.split("-", 1)
                if quote == "USD" and base:
                    symbols.add(f"{base}USD")
            else:
                symbols.add(cleaned)
        return symbols

    def _high_risk_sprint_universe(self) -> list[UniverseTicker]:
        configured = [item.strip().upper() for item in settings.high_risk_sprint_symbols.split(",") if item.strip()]
        symbols = configured or list(DEFAULT_HIGH_RISK_SPRINT_SYMBOLS)
        return [UniverseTicker(symbol, "equity", "US") for symbol in symbols]

    def _scan_universe(self, *, goal_pressure_multiplier: float) -> list[tuple[UniverseTicker, bool]]:
        scan_universe: list[tuple[UniverseTicker, bool]] = [(ticker, False) for ticker in UNIVERSE]
        if not self._high_risk_sprint_active(goal_pressure_multiplier=goal_pressure_multiplier):
            return scan_universe

        existing_symbols = {ticker.symbol for ticker in UNIVERSE}
        for ticker in self._high_risk_sprint_universe():
            if ticker.symbol in existing_symbols:
                continue
            scan_universe.append((ticker, True))
        return scan_universe

    def _prefilter(self, ticker: UniverseTicker, *, sprint_mode: bool = False) -> dict | None:
        end = datetime.now(tz=timezone.utc)
        start = end - timedelta(days=180)
        df = historical_data_service.load_historical_data(
            symbol=ticker.symbol,
            timeframe="1d",
            start_date=start,
            end_date=end,
        )
        close = [float(v) for v in df["close"].tolist() if float(v) > 0]
        high = [float(v) for v in df["high"].tolist() if float(v) > 0]
        low = [float(v) for v in df["low"].tolist() if float(v) > 0]
        volume = [float(v) for v in df["volume"].tolist()]
        if len(close) < 25:
            return None

        returns = [(close[i] / close[i - 1]) - 1.0 for i in range(1, len(close))]
        realized_vol = (sum((r - (sum(returns) / len(returns))) ** 2 for r in returns) / len(returns)) ** 0.5

        avg_dollar_volume = sum(c * v for c, v in zip(close[-30:], volume[-30:])) / min(len(close[-30:]), len(volume[-30:]))
        spread_proxy = sum((h - l) / max(c, 1e-6) for h, l, c in zip(high[-30:], low[-30:], close[-30:])) / max(len(close[-30:]), 1)
        momentum_20d = (close[-1] / close[-20]) - 1.0

        if sprint_mode:
            last_price = close[-1]
            if ticker.asset_class != "equity":
                return None
            if last_price < 0.75 or last_price > settings.high_risk_sprint_max_price:
                return None
            if avg_dollar_volume < settings.high_risk_sprint_min_dollar_volume:
                return None
            if spread_proxy > settings.high_risk_sprint_max_spread_proxy:
                return None

            prefilter_score = momentum_20d * 110 + realized_vol * 12 - spread_proxy * 18
            return {
                "symbol": ticker.symbol,
                "asset_class": ticker.asset_class,
                "region": ticker.region,
                "avg_dollar_volume": avg_dollar_volume,
                "spread_proxy": spread_proxy,
                "realized_volatility_pct": max(0.001, min(realized_vol, 0.35)),
                "momentum_20d": momentum_20d,
                "prefilter_score": prefilter_score,
                "last_price": last_price,
                "scan_mode": "high_risk_sprint",
            }

        if ticker.asset_class == "crypto":
            min_liquidity = 2_000_000
        elif ticker.asset_class == "etf":
            min_liquidity = 7_000_000
        else:
            min_liquidity = 10_000_000
        if avg_dollar_volume < min_liquidity:
            return None
        if spread_proxy > 0.08:
            return None

        prefilter_score = momentum_20d * 100 + realized_vol * 8 - spread_proxy * 25
        return {
            "symbol": ticker.symbol,
            "asset_class": ticker.asset_class,
            "region": ticker.region,
            "avg_dollar_volume": avg_dollar_volume,
            "spread_proxy": spread_proxy,
            "realized_volatility_pct": max(0.001, min(realized_vol, 0.25)),
            "momentum_20d": momentum_20d,
            "prefilter_score": prefilter_score,
            "last_price": close[-1],
            "scan_mode": "core",
        }

    def _execution_viability(self, *, symbol: str, asset_class: str, action: str) -> tuple[str, bool, str | None]:
        mode = execution_bridge.get_mode()
        broker = broker_router.route_broker(symbol=symbol, liquidity_score=1.0, mode=mode)

        if action == "HOLD":
            return broker, False, "No directional edge."

        if mode == "SIMULATION":
            return broker, False, "Execution mode is SIMULATION."

        if broker == "coinbase":
            if asset_class != "crypto":
                return broker, False, "Coinbase route only supports crypto assets."

            if not settings.coinbase_api_key_name or not settings.coinbase_api_private_key:
                return broker, False, "Coinbase credentials are missing."

            if not settings.coinbase_live_trading_enabled:
                return broker, False, "Coinbase live trading is disabled."

            if mode != "LIVE_TRADING":
                return broker, False, "Coinbase execution requires LIVE_TRADING mode."

            upper = symbol.upper()
            normalized = f"{upper[:-3]}-USD" if upper.endswith("USD") and len(upper) > 3 else upper
            allowlist = {item.strip().upper() for item in settings.coinbase_trade_products.split(",") if item.strip()}
            if normalized not in allowlist:
                return broker, False, f"{normalized} is not in COINBASE_TRADE_PRODUCTS allowlist."

            return broker, True, None

        if broker == "tradier":
            if asset_class != "equity":
                return broker, False, "Tradier route currently supports equities in this engine."

            if not settings.tradier_effective_api_key or not settings.tradier_effective_account_number:
                return broker, False, "Tradier credentials are missing."

            if not settings.tradier_live_trading_enabled:
                return broker, False, "Tradier live trading is disabled."

            if mode != "LIVE_TRADING":
                return broker, False, "Tradier execution requires LIVE_TRADING mode."

            return broker, True, None

        # Alpaca route
        if not settings.alpaca_api_key or not settings.alpaca_secret_key:
            return broker, False, "Alpaca credentials are missing."

        if mode == "LIVE_TRADING" and settings.alpaca_paper:
            return broker, False, "LIVE_TRADING with Alpaca requires ALPACA_PAPER=false."

        if mode == "PAPER_TRADING" and not settings.alpaca_paper:
            return broker, False, "PAPER_TRADING with Alpaca requires ALPACA_PAPER=true."

        return broker, True, None

    @staticmethod
    def _apply_notional_scale(item: dict, *, new_notional: float) -> None:
        old_notional = float(item.get("recommended_notional", 0.0) or 0.0)
        if old_notional <= 0.0 or new_notional <= 0.0:
            return
        scale = new_notional / old_notional
        item["recommended_notional"] = new_notional
        item["recommended_qty"] = float(item.get("recommended_qty", 0.0) or 0.0) * scale
        item["target_pct"] = max(0.005, float(item.get("target_pct", 0.0) or 0.0) * scale)

    def _redistribute_post_cap_slack(
        self,
        *,
        tradable: list[dict],
        target_total_notional: float,
        strategy_cap_base_notional: float,
        cluster_cap_base_notional: float,
        max_strategy_share: float,
        max_cluster_share: float,
    ) -> dict:
        if not tradable:
            return {
                "applied": False,
                "target_total_notional": round(target_total_notional, 2),
                "pre_reconcile_notional": 0.0,
                "post_reconcile_notional": 0.0,
                "slack_before": 0.0,
                "slack_filled": 0.0,
                "remaining_slack": 0.0,
                "adjustments": [],
            }

        current_total = sum(float(item.get("recommended_notional", 0.0) or 0.0) for item in tradable)
        slack = max(0.0, float(target_total_notional) - current_total)
        if slack <= 1.0:
            return {
                "applied": False,
                "target_total_notional": round(target_total_notional, 2),
                "pre_reconcile_notional": round(current_total, 2),
                "post_reconcile_notional": round(current_total, 2),
                "slack_before": round(slack, 2),
                "slack_filled": 0.0,
                "remaining_slack": round(slack, 2),
                "adjustments": [],
            }

        strategy_cap_amount = max(0.0, float(strategy_cap_base_notional) * max_strategy_share)
        cluster_cap_amount = max(0.0, float(cluster_cap_base_notional) * max_cluster_share)
        symbol_adjustments: dict[str, float] = {}
        slack_before = slack

        for _ in range(6):
            if slack <= 1.0:
                break

            strategy_totals: dict[str, float] = {}
            cluster_totals: dict[str, float] = {}
            for item in tradable:
                strategy = str(item.get("recommended_trade", "UNKNOWN")).upper()
                cluster = str(item.get("correlation_cluster") or "unknown")
                notional = float(item.get("recommended_notional", 0.0) or 0.0)
                strategy_totals[strategy] = strategy_totals.get(strategy, 0.0) + notional
                cluster_totals[cluster] = cluster_totals.get(cluster, 0.0) + notional

            eligible: list[tuple[dict, float, float]] = []
            for item in tradable:
                strategy = str(item.get("recommended_trade", "UNKNOWN")).upper()
                cluster = str(item.get("correlation_cluster") or "unknown")
                strategy_headroom = max(0.0, strategy_cap_amount - strategy_totals.get(strategy, 0.0))
                cluster_headroom = max(0.0, cluster_cap_amount - cluster_totals.get(cluster, 0.0))
                capacity = min(strategy_headroom, cluster_headroom)
                if capacity <= 0.0:
                    continue
                notional = float(item.get("recommended_notional", 0.0) or 0.0)
                if notional <= 0.0:
                    continue
                confidence = max(0.05, min(float(item.get("consensus_confidence", 0.5) or 0.5), 1.0))
                win_rate = max(0.25, min(float(item.get("learning_recent_win_rate", 0.5) or 0.5), 0.90))
                cluster_share = cluster_totals.get(cluster, 0.0) / max(current_total, 1e-9)
                low_correlation_bonus = max(0.70, min(1.30, 1.15 - cluster_share))
                drawdown_resilience = max(0.35, min(float(item.get("drawdown_resilience", 0.8) or 0.8), 1.25))
                priority_score = confidence * win_rate * low_correlation_bonus * drawdown_resilience
                item["capital_priority_score"] = round(priority_score, 6)
                eligible.append((item, capacity, max(0.01, priority_score)))

            if not eligible:
                break

            total_weight = sum(weight for _, _, weight in eligible)
            if total_weight <= 0.0:
                break

            allocated_this_round = 0.0
            for item, capacity, weight in eligible:
                desired = slack * (weight / total_weight)
                add_notional = min(capacity, desired)
                if add_notional <= 0.0:
                    continue
                symbol = str(item.get("symbol", "UNKNOWN"))
                current_notional = float(item.get("recommended_notional", 0.0) or 0.0)
                self._apply_notional_scale(item, new_notional=current_notional + add_notional)
                symbol_adjustments[symbol] = symbol_adjustments.get(symbol, 0.0) + add_notional
                allocated_this_round += add_notional

            if allocated_this_round <= 0.0:
                break
            slack = max(0.0, slack - allocated_this_round)

        for item in tradable:
            item["recommended_notional"] = round(float(item.get("recommended_notional", 0.0) or 0.0), 2)
            item["recommended_qty"] = round(float(item.get("recommended_qty", 0.0) or 0.0), 6)
            item["target_pct"] = round(max(0.005, float(item.get("target_pct", 0.0) or 0.0)), 6)

        post_total = sum(float(item.get("recommended_notional", 0.0) or 0.0) for item in tradable)
        adjustments = [
            {
                "symbol": symbol,
                "added_notional": round(added, 2),
            }
            for symbol, added in sorted(symbol_adjustments.items(), key=lambda x: x[1], reverse=True)
        ]
        return {
            "applied": bool(adjustments),
            "target_total_notional": round(target_total_notional, 2),
            "pre_reconcile_notional": round(current_total, 2),
            "post_reconcile_notional": round(post_total, 2),
            "slack_before": round(slack_before, 2),
            "slack_filled": round(max(0.0, slack_before - slack), 2),
            "remaining_slack": round(slack, 2),
            "adjustments": adjustments,
        }

    def scan(
        self,
        *,
        limit: int,
        account_balance: float,
        drawdown_pct: float,
        current_exposure_pct: float,
        goal_pressure_multiplier: float,
    ) -> dict:
        quality = execution_quality_engine.summary(limit=500)
        symbol_quality = quality.get("symbol_quality", {})
        asset_quality = quality.get("asset_class_quality", {})
        regime_quality = quality.get("regime_quality", {})
        strategy_quality = quality.get("strategy_quality", {})
        confidence_band_quality = quality.get("confidence_band_quality", {})
        bucket_quality = quality.get("bucket_quality", {})
        disabled_strategies = {str(name).upper() for name in quality.get("disabled_strategies", [])}
        probation_strategies = {str(name).upper() for name in quality.get("probation_strategies", [])}
        forced_retest_strategies = {str(name).upper() for name in quality.get("forced_retest_strategies", [])}
        live_mode = live_experiment_promotion_service.status()
        meta_risk = meta_risk_governor.evaluate(drawdown_pct=drawdown_pct)
        system_mode = system_mode_service.evaluate(
            goal_pressure=goal_pressure_multiplier,
            drawdown_pct=drawdown_pct,
            quality=quality,
            meta_risk=meta_risk,
            live_mode=live_mode,
        )
        frozen_strategies = {str(name).upper() for name in meta_risk.get("frozen_strategies", [])}
        disabled_strategies.update(frozen_strategies)

        system_controls = system_mode.get("controls", {}) or {}
        system_trade_frequency = max(0.35, min(float(system_controls.get("trade_frequency_multiplier", 1.0) or 1.0), 1.25))
        system_confidence_floor = max(0.50, float(system_controls.get("min_confidence_floor", 0.56) or 0.56))

        evolution_enabled = bool(live_mode.get("enable_evolution", True)) and not bool(
            meta_risk.get("disable_evolution_temporarily", False)
        ) and bool(system_controls.get("allow_evolution", True))
        compounding_enabled = bool(live_mode.get("enable_compounding", True)) and bool(
            system_controls.get("allow_compounding", True)
        )
        global_risk_multiplier = float(meta_risk.get("global_exposure_multiplier", 1.0) or 1.0) * float(
            system_controls.get("allocation_multiplier", 1.0) or 1.0
        )

        evolution = (
            strategy_evolution_service.plan(strategy_quality=strategy_quality)
            if evolution_enabled
            else {"mutations": [], "clones": [], "reinforcement_weights": {}, "suggested_experiments": 0}
        )
        reinforcement_weights = evolution.get("reinforcement_weights", {})
        risk_posture = mission_policy_engine.risk_posture(drawdown_pct)
        posture_mode = str(risk_posture.get("mode", "normal"))

        prefiltered: list[dict] = []
        sprint_active = self._high_risk_sprint_active(goal_pressure_multiplier=goal_pressure_multiplier)
        scan_universe = self._scan_universe(goal_pressure_multiplier=goal_pressure_multiplier)
        for ticker, sprint_mode in scan_universe:
            try:
                result = self._prefilter(ticker, sprint_mode=sprint_mode)
            except Exception as exc:
                logger.warning("prefilter_failed symbol=%s error=%s", ticker.symbol, exc)
                continue
            if result:
                prefiltered.append(result)

        prefiltered = sorted(prefiltered, key=lambda item: item["prefilter_score"], reverse=True)
        candidate_window = min(max(limit * 2, 10), 30)
        candidates = prefiltered[:candidate_window]

        # Ensure Coinbase-priority crypto symbols are always evaluated if available.
        priority_symbols = self._coinbase_priority_symbols()
        existing_symbols = {item["symbol"] for item in candidates}
        for item in prefiltered:
            if item["symbol"] in priority_symbols and item["symbol"] not in existing_symbols:
                candidates.append(item)
                existing_symbols.add(item["symbol"])

        # Add a small crypto tail so crypto ideas are not drowned out by equities/ETFs.
        crypto_tail = [item for item in prefiltered if item["asset_class"] == "crypto"][:8]
        for item in crypto_tail:
            if item["symbol"] not in existing_symbols:
                candidates.append(item)
                existing_symbols.add(item["symbol"])

        if sprint_active:
            sprint_tail = [item for item in prefiltered if item.get("scan_mode") == "high_risk_sprint"][:6]
            for item in sprint_tail:
                if item["symbol"] not in existing_symbols:
                    candidates.append(item)
                    existing_symbols.add(item["symbol"])

        opportunities: list[dict] = []
        for candidate in candidates:
            symbol = candidate["symbol"]
            try:
                forecast = kronos_service.generate_forecast(symbol=symbol, timeframe="1d")
                regime = regime_detector.detect(symbol=symbol, timeframe="1d")
                options_data = options_service.get_options_chain(symbol=symbol)
                outputs = agent_manager.run_agents(
                    symbol=symbol,
                    forecast=forecast,
                    options_data=options_data,
                    regime=regime.regime,
                )
                signal = signal_engine.generate_signal(symbol=symbol, forecast=forecast, options_data=options_data)
                swarm = consensus_engine.generate_consensus(symbol=symbol, outputs=outputs)
                news = news_intelligence.analyze_symbol(symbol)
                context = context_intelligence.get_context(symbol)
                expected_return_pct = 0.0
                if forecast.forecast_prices:
                    expected_return_pct = (forecast.forecast_prices[-1] / options_data.underlying_price) - 1.0

                action = {
                    "BULLISH": "BUY",
                    "BEARISH": "SELL",
                    "NEUTRAL": "HOLD",
                }.get(swarm.consensus.final_bias, "HOLD")
                agreement = (
                    sum(1 for item in outputs if item.bias == swarm.consensus.final_bias) / len(outputs)
                    if outputs
                    else 0.0
                )
                risk_level = "HIGH" if regime.regime == "HIGH_VOLATILITY" else "MEDIUM" if regime.regime == "RANGE_BOUND" else "LOW"

                confidence = float(swarm.consensus.confidence)
                if confidence < 0.55:
                    conf_band = "low"
                elif confidence < 0.65:
                    conf_band = "mid"
                elif confidence < 0.75:
                    conf_band = "high"
                else:
                    conf_band = "very_high"
                confidence_band_score = float((confidence_band_quality.get(conf_band) or {}).get("quality_score", 0.5) or 0.5)
                strategy_name = str(swarm.recommended_trade).upper()
                strategy_score = float((strategy_quality.get(strategy_name) or {}).get("quality_score", 0.5) or 0.5)
                reinforcement = float(reinforcement_weights.get(strategy_name, 1.0) or 1.0)
                strategy_score = max(0.0, min(strategy_score * reinforcement, 1.0))
                strategy_mutation = next(
                    (m for m in evolution.get("mutations", []) if str(m.get("strategy", "")).upper() == strategy_name),
                    None,
                )
                strategy_clone = next(
                    (c for c in evolution.get("clones", []) if str(c.get("strategy", "")).upper() == strategy_name),
                    None,
                )
                strategy_disabled = strategy_name in disabled_strategies or "SWARM_MARKET" in disabled_strategies
                strategy_probation = strategy_name in probation_strategies or "SWARM_MARKET" in probation_strategies
                strategy_forced_retest = strategy_name in forced_retest_strategies or "SWARM_MARKET" in forced_retest_strategies
                regime_score = float((regime_quality.get(str(regime.regime).upper()) or {}).get("quality_score", 0.5) or 0.5)
                recent_win_rate = max(0.35, min((regime_score + strategy_score + confidence_band_score) / 3.0, 0.75))
                compounding = compounding_engine.plan(
                    goal_pressure=goal_pressure_multiplier,
                    drawdown_pct=drawdown_pct,
                    recent_win_rate=recent_win_rate,
                )
                if not compounding_enabled:
                    compounding = {
                        **compounding,
                        "reinvestment_multiplier": 1.0,
                        "risk_budget_multiplier": 1.0,
                    }

                allocation = capital_allocator.compute(
                    AllocationInput(
                        account_balance=account_balance,
                        current_price=options_data.underlying_price,
                        confidence=swarm.consensus.confidence,
                        regime=regime.regime,
                        risk_level=risk_level,
                        agent_agreement=agreement,
                        drawdown_pct=drawdown_pct,
                        current_exposure_pct=current_exposure_pct,
                        realized_volatility_pct=float(candidate["realized_volatility_pct"]),
                        goal_pressure_multiplier=goal_pressure_multiplier * float(context["modifiers"]["risk_modifier"]),
                        recent_win_rate=recent_win_rate,
                    )
                )
                allocation = dict(allocation)
                reinvestment_multiplier = float(compounding.get("reinvestment_multiplier", 1.0) or 1.0)
                risk_budget_multiplier = float(compounding.get("risk_budget_multiplier", 1.0) or 1.0)
                allocation["target_pct"] = round(min(0.60, max(0.01, float(allocation["target_pct"]) * reinvestment_multiplier)), 6)
                allocation["recommended_notional"] = round(float(allocation["recommended_notional"]) * reinvestment_multiplier, 2)
                allocation["recommended_qty"] = round(float(allocation["recommended_qty"]) * reinvestment_multiplier, 6)
                allocation["max_risk_amount"] = round(float(allocation["max_risk_amount"]) * risk_budget_multiplier, 2)

                if global_risk_multiplier < 1.0:
                    allocation["target_pct"] = round(max(0.005, float(allocation["target_pct"]) * global_risk_multiplier), 6)
                    allocation["recommended_notional"] = round(float(allocation["recommended_notional"]) * global_risk_multiplier, 2)
                    allocation["recommended_qty"] = round(float(allocation["recommended_qty"]) * global_risk_multiplier, 6)
                    allocation["max_risk_amount"] = round(float(allocation["max_risk_amount"]) * global_risk_multiplier, 2)

                if posture_mode == "recovery_forced":
                    allocation["target_pct"] = round(max(0.01, float(allocation["target_pct"]) * 0.80), 6)
                    allocation["recommended_notional"] = round(float(allocation["recommended_notional"]) * 0.80, 2)
                    allocation["recommended_qty"] = round(float(allocation["recommended_qty"]) * 0.80, 6)
                    allocation["max_risk_amount"] = round(float(allocation["max_risk_amount"]) * 0.85, 2)
                elif posture_mode == "capital_preservation_only":
                    allocation["target_pct"] = round(max(0.005, float(allocation["target_pct"]) * 0.60), 6)
                    allocation["recommended_notional"] = round(float(allocation["recommended_notional"]) * 0.60, 2)
                    allocation["recommended_qty"] = round(float(allocation["recommended_qty"]) * 0.60, 6)
                    allocation["max_risk_amount"] = round(float(allocation["max_risk_amount"]) * 0.70, 2)

                if strategy_probation:
                    allocation["target_pct"] = round(max(0.01, float(allocation["target_pct"]) * 0.65), 6)
                    allocation["recommended_notional"] = round(float(allocation["recommended_notional"]) * 0.65, 2)
                    allocation["recommended_qty"] = round(float(allocation["recommended_qty"]) * 0.65, 6)
                    allocation["max_risk_amount"] = round(float(allocation["max_risk_amount"]) * 0.75, 2)

                if strategy_forced_retest:
                    allocation["target_pct"] = round(max(0.01, float(allocation["target_pct"]) * 0.55), 6)
                    allocation["recommended_notional"] = round(float(allocation["recommended_notional"]) * 0.55, 2)
                    allocation["recommended_qty"] = round(float(allocation["recommended_qty"]) * 0.55, 6)
                    allocation["max_risk_amount"] = round(float(allocation["max_risk_amount"]) * 0.65, 2)

                risk = risk_engine.evaluate_trade(
                    entry_price=options_data.underlying_price,
                    stop_loss_pct=float(allocation["stop_loss_pct"]),
                    take_profit_pct=min(
                        0.12,
                        max(0.03, float(allocation["stop_loss_pct"]) * 1.9),
                    ),
                    confidence=swarm.consensus.confidence,
                    max_loss_amount=float(allocation["max_risk_amount"]),
                    account_balance=account_balance,
                )

                routed_broker, broker_viable, broker_block_reason = self._execution_viability(
                    symbol=symbol,
                    asset_class=candidate["asset_class"],
                    action=action,
                )
                if strategy_disabled:
                    broker_viable = False
                    broker_block_reason = (
                        f"Strategy frozen by meta-risk/thrash guard: {strategy_name}"
                        if strategy_name in frozen_strategies
                        else f"Strategy auto-disabled by kill switch: {strategy_name}"
                    )
                elif strategy_probation and confidence < 0.60:
                    broker_viable = False
                    broker_block_reason = f"Strategy in probation mode requires >= 0.60 confidence: {strategy_name}"
                elif strategy_forced_retest and confidence < 0.58:
                    broker_viable = False
                    broker_block_reason = f"Strategy in forced re-test mode requires >= 0.58 confidence: {strategy_name}"
                elif confidence < system_confidence_floor:
                    broker_viable = False
                    broker_block_reason = (
                        f"System mode {system_mode.get('mode', 'BALANCED')} requires >= {system_confidence_floor:.2f} confidence"
                    )
                elif posture_mode == "capital_preservation_only" and risk_level == "HIGH":
                    broker_viable = False
                    broker_block_reason = "Capital-preservation posture blocks high-risk setups."
                tradable = action != "HOLD" and allocation["accepted"] and risk["approved"] and broker_viable and not strategy_disabled
                validation = context.get("signal_validation", {})
                reaction = context.get("market_reaction", {})
                validated_strength = float(validation.get("validated_signal_strength", 0.0))
                reaction_score = float(reaction.get("correlation_score", 0.0))

                # If consensus is neutral, allow strong context + expected return to
                # express a directional preference so opportunities can progress beyond WATCH.
                directional_edge = (
                    expected_return_pct * 2.4
                    + float(news["sentiment_score"]) * 0.55
                    + (float(news["news_momentum_score"]) - 0.5) * 0.22
                    + validated_strength * 0.28
                    + reaction_score * 0.24
                )
                if action == "HOLD" and swarm.consensus.confidence >= 0.52:
                    if directional_edge >= 0.12:
                        action = "BUY"
                    elif directional_edge <= -0.12:
                        action = "SELL"

                news_alpha_boost = (
                    float(news["sentiment_score"]) * 0.06
                    + float(news["news_momentum_score"]) * 0.05
                    + float(news["event_strength"]) * 0.04
                    + validated_strength * 0.08
                    + max(0.0, reaction_score) * 0.06
                )

                sym_quality_score = float((symbol_quality.get(symbol.upper()) or {}).get("quality_score", 0.5) or 0.5)
                drawdown_resilience = max(
                    0.35,
                    min(
                        1.25,
                        1.05 - drawdown_pct * 2.0 + sym_quality_score * 0.25 - float(candidate["realized_volatility_pct"]) * 0.70,
                    ),
                )
                class_quality_score = float((asset_quality.get(candidate["asset_class"]) or {}).get("quality_score", 0.5) or 0.5)
                execution_quality_adjustment = (sym_quality_score - 0.5) * 0.24 + (class_quality_score - 0.5) * 0.14
                confidence_band_adjustment = (confidence_band_score - 0.5) * 0.12
                persistence = opportunity_persistence_store.score(
                    symbol=symbol,
                    score=float(candidate.get("prefilter_score", 0.0)),
                    confidence=float(swarm.consensus.confidence),
                    regime=str(regime.regime),
                    news_strength=float(news.get("event_strength", 0.0)),
                    volume_spike=float(candidate.get("avg_dollar_volume", 0.0)),
                )

                risk_adjusted_score = (
                    (swarm.consensus.confidence * float(context["modifiers"]["confidence_modifier"])) * 0.45
                    + max(0.0, risk["expected_value"]) * 8.0 * 0.2
                    + float(allocation["target_pct"]) * 3.0 * 0.2
                    + (0.15 if tradable else 0.0)
                    + (0.05 if broker_viable else -0.03)
                    + news_alpha_boost
                    + float(context["modifiers"]["opportunity_boost"])
                    + execution_quality_adjustment
                    + confidence_band_adjustment
                    + float(persistence.get("total_bonus", 0.0))
                    - (0.03 if strategy_forced_retest else 0.0)
                    - (0.06 if strategy_probation else 0.0)
                )
            except Exception as exc:
                logger.warning("candidate_scan_failed symbol=%s error=%s", symbol, exc)
                continue

            opportunities.append(
                {
                    "symbol": symbol,
                    "asset_class": candidate["asset_class"],
                    "region": candidate["region"],
                    "regime": regime.regime,
                    "regime_confidence": regime.confidence,
                    "signal": signal.signal,
                    "recommended_trade": swarm.recommended_trade,
                    "consensus_bias": swarm.consensus.final_bias,
                    "consensus_confidence": swarm.consensus.confidence,
                    "expected_return_pct": round(expected_return_pct, 6),
                    "sentiment_score": news["sentiment_score"],
                    "news_momentum_score": news["news_momentum_score"],
                    "event_strength": news["event_strength"],
                    "data_classification": news["data_classification"],
                    "sources_used": news["sources_used"],
                    "event_flags": news["event_flags"],
                    "context_modifiers": context["modifiers"],
                    "signal_validation": context.get("signal_validation", {}),
                    "market_reaction": context.get("market_reaction", {}),
                    "risk_level": risk["risk_level"],
                    "broker": routed_broker,
                    "broker_ready": broker_viable,
                    "broker_block_reason": broker_block_reason,
                    "expected_value": risk["expected_value"],
                    "target_pct": allocation["target_pct"],
                    "recommended_notional": allocation["recommended_notional"],
                    "recommended_qty": allocation["recommended_qty"],
                    "compounding": compounding,
                    "goal_pressure_multiplier": goal_pressure_multiplier,
                    "realized_volatility_pct": candidate["realized_volatility_pct"],
                    "avg_dollar_volume": round(candidate["avg_dollar_volume"], 2),
                    "spread_proxy": round(candidate["spread_proxy"], 6),
                    "prefilter_score": round(candidate["prefilter_score"], 6),
                    "scan_mode": candidate.get("scan_mode", "core"),
                    "persistence": persistence,
                    "execution_quality_score": round(sym_quality_score, 4),
                    "learning_recent_win_rate": round(recent_win_rate, 4),
                    "strategy_disabled": strategy_disabled,
                    "strategy_probation": strategy_probation,
                    "strategy_forced_retest": strategy_forced_retest,
                    "drawdown_resilience": round(drawdown_resilience, 6),
                    "strategy_state": "disabled" if strategy_disabled else "forced_retest" if strategy_forced_retest else "probation" if strategy_probation else "enabled",
                    "reinforcement_weight": round(reinforcement, 4),
                    "strategy_evolution_hint": {
                        "mutation": strategy_mutation,
                        "clone": strategy_clone,
                    },
                    "tradable": tradable,
                    "risk_adjusted_score": round(risk_adjusted_score, 6),
                    "opportunity_score": round(risk_adjusted_score, 6),
                    "explainability": build_explainability(
                        reasoning=(
                            f"Consensus={swarm.consensus.final_bias} ({swarm.consensus.confidence:.2f}), "
                            f"signal={signal.signal}, regime={regime.regime}."
                        ),
                        confidence=swarm.consensus.confidence,
                        risk_level=risk["risk_level"],
                        expected_value=risk["expected_value"],
                        accepted=tradable,
                        safeguards=["prefilter", "risk_engine", "capital_allocator"],
                        inputs={
                            "expected_return_pct": round(expected_return_pct, 6),
                            "target_pct": allocation["target_pct"],
                            "goal_pressure_multiplier": goal_pressure_multiplier,
                            "sentiment_score": news["sentiment_score"],
                            "news_momentum_score": news["news_momentum_score"],
                            "event_strength": news["event_strength"],
                            "context_modifiers": context["modifiers"],
                            "signal_validation": context.get("signal_validation", {}),
                            "market_reaction": context.get("market_reaction", {}),
                        },
                    ),
                }
            )

        dominant_regime = (
            max(
                (str(item.get("regime", "RANGE_BOUND")) for item in opportunities),
                key=lambda reg: sum(1 for x in opportunities if str(x.get("regime", "RANGE_BOUND")) == reg),
                default="RANGE_BOUND",
            )
            if opportunities
            else "RANGE_BOUND"
        )
        mission = mission_policy_engine.mission_snapshot(
            goal_status={"goal_pressure_multiplier": goal_pressure_multiplier, "stress_level": "HIGH" if goal_pressure_multiplier >= 1.4 else "MEDIUM"},
            drawdown_pct=drawdown_pct,
            sprint_active=sprint_active,
            dominant_regime=dominant_regime,
            regime_quality=regime_quality,
            bucket_quality=bucket_quality,
            system_mode=system_mode,
        )

        bucket_weights = mission.get("capital_buckets", {})
        for item in opportunities:
            bucket = self._bucket_for(item)
            item["capital_bucket"] = bucket
            item["capital_bucket_weight"] = float(bucket_weights.get(bucket, 0.25))
            bucket_boost = (float(bucket_weights.get(bucket, 0.25)) - 0.25) * 0.18
            item["opportunity_score"] = round(float(item["opportunity_score"]) + bucket_boost, 6)
            item["why_trade_exists"] = {
                "persistence_bonus": round(float((item.get("persistence") or {}).get("total_bonus", 0.0) or 0.0), 6),
                "strategy_win_rate": round(float(item.get("learning_recent_win_rate", 0.0) or 0.0), 4),
                "bucket_weight": round(float(item.get("capital_bucket_weight", 0.25) or 0.25), 4),
                "execution_quality": round(float(item.get("execution_quality_score", 0.0) or 0.0), 4),
                "strategy_state": str(item.get("strategy_state", "enabled")),
            }

        ranked = sorted(opportunities, key=lambda item: item["opportunity_score"], reverse=True)
        effective_limit = max(3, min(limit, int(round(limit * system_trade_frequency))))

        # Bucket-aware selection to prevent one theme from consuming all slots.
        bucket_quota = {
            bucket: max(1, int(round(float(weight) * max(effective_limit, 1))))
            for bucket, weight in bucket_weights.items()
        }
        bucket_used = {key: 0 for key in bucket_quota}

        # Keep score ordering, but reserve slots for crypto diversity when available.
        crypto_quota = min(max(1, effective_limit // 4), effective_limit)
        selected: list[dict] = []
        selected_symbols: set[str] = set()

        for item in ranked:
            if len(selected) >= crypto_quota:
                break
            if item["asset_class"] != "crypto":
                continue
            selected.append(item)
            selected_symbols.add(item["symbol"])

        for item in ranked:
            if len(selected) >= effective_limit:
                break
            if item["symbol"] in selected_symbols:
                continue
            bucket = item.get("capital_bucket", "core_trend")
            if bucket in bucket_quota and bucket_used.get(bucket, 0) >= bucket_quota[bucket]:
                continue
            selected.append(item)
            selected_symbols.add(item["symbol"])
            if bucket in bucket_used:
                bucket_used[bucket] += 1

        top = selected[:effective_limit]
        opportunity_persistence_store.record_batch(top)

        tradable = [item for item in top if item["tradable"]]
        concentration_adjustments: list[dict] = []
        pre_total_notional = sum(float(item["recommended_notional"]) for item in tradable)
        strategy_notional: dict[str, float] = {}
        for item in tradable:
            key = str(item.get("recommended_trade", "UNKNOWN")).upper()
            strategy_notional[key] = strategy_notional.get(key, 0.0) + float(item["recommended_notional"])

        max_strategy_share = 0.55
        for strategy, notional in strategy_notional.items():
            cap = pre_total_notional * max_strategy_share
            if pre_total_notional <= 0.0 or notional <= cap:
                continue
            scale = cap / max(notional, 1e-9)
            for item in tradable:
                if str(item.get("recommended_trade", "UNKNOWN")).upper() != strategy:
                    continue
                item["recommended_notional"] = round(float(item["recommended_notional"]) * scale, 2)
                item["recommended_qty"] = round(float(item["recommended_qty"]) * scale, 6)
                item["target_pct"] = round(max(0.005, float(item["target_pct"]) * scale), 6)
                guard = item.get("concentration_guard") or {}
                guard.update(
                    {
                        "applied": True,
                        "strategy": strategy,
                        "scale": round(scale, 4),
                        "max_strategy_share": max_strategy_share,
                    }
                )
                item["concentration_guard"] = guard
            concentration_adjustments.append(
                {
                    "strategy": strategy,
                    "before_notional": round(notional, 2),
                    "after_cap_notional": round(cap, 2),
                    "max_share": max_strategy_share,
                }
            )

        # Cross-strategy correlation awareness guard.
        correlation_adjustments: list[dict] = []
        cluster_totals: dict[str, float] = {}
        pre_corr_total_notional = sum(float(item["recommended_notional"]) for item in tradable)
        for item in tradable:
            cluster = f"{item.get('asset_class','unknown')}:{item.get('consensus_bias','NEUTRAL')}:{item.get('capital_bucket','core_trend')}"
            item["correlation_cluster"] = cluster
            cluster_totals[cluster] = cluster_totals.get(cluster, 0.0) + float(item["recommended_notional"])

        max_cluster_share = 0.70
        for cluster, notional in cluster_totals.items():
            cap = pre_corr_total_notional * max_cluster_share
            if pre_corr_total_notional <= 0.0 or notional <= cap:
                continue
            scale = cap / max(notional, 1e-9)
            for item in tradable:
                if item.get("correlation_cluster") != cluster:
                    continue
                item["recommended_notional"] = round(float(item["recommended_notional"]) * scale, 2)
                item["recommended_qty"] = round(float(item["recommended_qty"]) * scale, 6)
                item["target_pct"] = round(max(0.005, float(item["target_pct"]) * scale), 6)
                guard = item.get("correlation_guard") or {}
                guard.update(
                    {
                        "applied": True,
                        "cluster": cluster,
                        "scale": round(scale, 4),
                        "max_cluster_share": max_cluster_share,
                    }
                )
                item["correlation_guard"] = guard
            correlation_adjustments.append(
                {
                    "cluster": cluster,
                    "before_notional": round(notional, 2),
                    "after_cap_notional": round(cap, 2),
                    "max_share": max_cluster_share,
                }
            )

        reconciliation = self._redistribute_post_cap_slack(
            tradable=tradable,
            target_total_notional=pre_total_notional,
            strategy_cap_base_notional=pre_total_notional,
            cluster_cap_base_notional=pre_corr_total_notional,
            max_strategy_share=max_strategy_share,
            max_cluster_share=max_cluster_share,
        )

        total_notional = sum(float(item["recommended_notional"]) for item in tradable)
        capital_split: list[dict] = []
        for item in tradable:
            notional = float(item["recommended_notional"])
            capital_split.append(
                {
                    "symbol": item["symbol"],
                    "strategy": str(item.get("recommended_trade", "UNKNOWN")),
                    "recommended_notional": round(notional, 2),
                    "allocation_weight": round(notional / total_notional, 6) if total_notional > 0 else 0.0,
                }
            )

        return {
            "scanned": len(scan_universe),
            "passed_prefilter": len(prefiltered),
            "opportunities": top,
            "capital_allocation_recommendations": capital_split,
            "capital_concentration_guard": {
                "max_strategy_share": max_strategy_share,
                "adjustments": concentration_adjustments,
            },
            "cross_strategy_correlation_guard": {
                "max_cluster_share": max_cluster_share,
                "adjustments": correlation_adjustments,
            },
            "capital_reconciliation": reconciliation,
            "mission_policy": mission,
            "system_mode": system_mode,
            "meta_risk_governor": meta_risk,
            "live_experiment_mode": live_mode,
            "strategy_evolution": evolution,
            "execution_quality": {
                "sample_size": quality.get("sample_size", 0),
                "asset_class_quality": asset_quality,
                "regime_quality": regime_quality,
                "strategy_quality": strategy_quality,
                "confidence_band_quality": confidence_band_quality,
                "bucket_quality": bucket_quality,
                "disabled_strategies": sorted(disabled_strategies),
                "probation_strategies": sorted(probation_strategies),
                "forced_retest_strategies": sorted(forced_retest_strategies),
            },
        }


opportunity_scanner = OpportunityScanner()
