from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.services.agent_manager import agent_manager
from app.services.capital_allocator import AllocationInput, capital_allocator
from app.services.consensus_engine import consensus_engine
from app.services.context_intelligence import context_intelligence
from app.services.explainability import build_explainability
from app.services.kronos_service import kronos_service
from app.services.news.news_intelligence import news_intelligence
from app.services.options_service import options_service
from app.services.regime_detector import regime_detector
from app.services.risk_engine import risk_engine
from app.services.signal_engine import signal_engine
from app.services.historical_data_service import historical_data_service


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


class OpportunityScanner:
    def _prefilter(self, ticker: UniverseTicker) -> dict | None:
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
        prefiltered: list[dict] = []
        for ticker in UNIVERSE:
            result = self._prefilter(ticker)
            if result:
                prefiltered.append(result)

        prefiltered = sorted(prefiltered, key=lambda item: item["prefilter_score"], reverse=True)
        candidates = prefiltered[: max(limit * 3, 10)]

        opportunities: list[dict] = []
        for candidate in candidates:
            symbol = candidate["symbol"]
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
                )
            )

            risk = risk_engine.evaluate_trade(
                entry_price=options_data.underlying_price,
                stop_loss_pct=float(allocation["stop_loss_pct"]),
                take_profit_pct=0.03,
                confidence=swarm.consensus.confidence,
                max_loss_amount=float(allocation["max_risk_amount"]),
                account_balance=account_balance,
            )

            tradable = action != "HOLD" and allocation["accepted"] and risk["approved"]
            validation = context.get("signal_validation", {})
            reaction = context.get("market_reaction", {})
            validated_strength = float(validation.get("validated_signal_strength", 0.0))
            reaction_score = float(reaction.get("correlation_score", 0.0))
            news_alpha_boost = (
                float(news["sentiment_score"]) * 0.06
                + float(news["news_momentum_score"]) * 0.05
                + float(news["event_strength"]) * 0.04
                + validated_strength * 0.08
                + max(0.0, reaction_score) * 0.06
            )
            risk_adjusted_score = (
                (swarm.consensus.confidence * float(context["modifiers"]["confidence_modifier"])) * 0.45
                + max(0.0, risk["expected_value"]) * 8.0 * 0.2
                + float(allocation["target_pct"]) * 3.0 * 0.2
                + (0.15 if tradable else 0.0)
                + news_alpha_boost
                + float(context["modifiers"]["opportunity_boost"])
            )

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
                    "expected_value": risk["expected_value"],
                    "target_pct": allocation["target_pct"],
                    "recommended_notional": allocation["recommended_notional"],
                    "recommended_qty": allocation["recommended_qty"],
                    "goal_pressure_multiplier": goal_pressure_multiplier,
                    "realized_volatility_pct": candidate["realized_volatility_pct"],
                    "avg_dollar_volume": round(candidate["avg_dollar_volume"], 2),
                    "spread_proxy": round(candidate["spread_proxy"], 6),
                    "prefilter_score": round(candidate["prefilter_score"], 6),
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

        ranked = sorted(opportunities, key=lambda item: item["opportunity_score"], reverse=True)
        top = ranked[:limit]

        tradable = [item for item in top if item["tradable"]]
        total_notional = sum(float(item["recommended_notional"]) for item in tradable)
        capital_split: list[dict] = []
        for item in tradable:
            notional = float(item["recommended_notional"])
            capital_split.append(
                {
                    "symbol": item["symbol"],
                    "recommended_notional": round(notional, 2),
                    "allocation_weight": round(notional / total_notional, 6) if total_notional > 0 else 0.0,
                }
            )

        return {
            "scanned": len(UNIVERSE),
            "passed_prefilter": len(prefiltered),
            "opportunities": top,
            "capital_allocation_recommendations": capital_split,
        }


opportunity_scanner = OpportunityScanner()
