from __future__ import annotations

from dataclasses import dataclass

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
from app.utils.data_loader import load_mock_ohlcv


@dataclass
class UniverseTicker:
    symbol: str
    asset_class: str
    region: str


UNIVERSE: list[UniverseTicker] = [
    UniverseTicker("AAPL", "equity", "US"),
    UniverseTicker("MSFT", "equity", "US"),
    UniverseTicker("NVDA", "equity", "US"),
    UniverseTicker("AMZN", "equity", "US"),
    UniverseTicker("GOOGL", "equity", "US"),
    UniverseTicker("META", "equity", "US"),
    UniverseTicker("TSLA", "equity", "US"),
    UniverseTicker("SPY", "equity", "US"),
    UniverseTicker("QQQ", "equity", "US"),
    UniverseTicker("XLF", "equity", "US"),
    UniverseTicker("XLE", "equity", "US"),
    UniverseTicker("EWJ", "equity", "JP"),
    UniverseTicker("EWU", "equity", "UK"),
    UniverseTicker("EEM", "equity", "EM"),
    UniverseTicker("BTCUSD", "crypto", "GLOBAL"),
    UniverseTicker("ETHUSD", "crypto", "GLOBAL"),
    UniverseTicker("SOLUSD", "crypto", "GLOBAL"),
    UniverseTicker("ADAUSD", "crypto", "GLOBAL"),
    UniverseTicker("DOGEUSD", "crypto", "GLOBAL"),
    UniverseTicker("JPM", "equity", "US"),
    UniverseTicker("BAC", "equity", "US"),
    UniverseTicker("WFC", "equity", "US"),
    UniverseTicker("GS", "equity", "US"),
    UniverseTicker("MS", "equity", "US"),
    UniverseTicker("UNH", "equity", "US"),
    UniverseTicker("LLY", "equity", "US"),
    UniverseTicker("JNJ", "equity", "US"),
    UniverseTicker("PFE", "equity", "US"),
    UniverseTicker("MRK", "equity", "US"),
    UniverseTicker("KO", "equity", "US"),
    UniverseTicker("PEP", "equity", "US"),
    UniverseTicker("PG", "equity", "US"),
    UniverseTicker("WMT", "equity", "US"),
    UniverseTicker("COST", "equity", "US"),
    UniverseTicker("HD", "equity", "US"),
    UniverseTicker("MCD", "equity", "US"),
    UniverseTicker("NKE", "equity", "US"),
    UniverseTicker("XOM", "equity", "US"),
    UniverseTicker("CVX", "equity", "US"),
    UniverseTicker("COP", "equity", "US"),
    UniverseTicker("SLB", "equity", "US"),
    UniverseTicker("BA", "equity", "US"),
    UniverseTicker("CAT", "equity", "US"),
    UniverseTicker("DE", "equity", "US"),
    UniverseTicker("GE", "equity", "US"),
    UniverseTicker("RTX", "equity", "US"),
    UniverseTicker("LMT", "equity", "US"),
    UniverseTicker("PLTR", "equity", "US"),
    UniverseTicker("SNOW", "equity", "US"),
    UniverseTicker("CRM", "equity", "US"),
    UniverseTicker("ORCL", "equity", "US"),
    UniverseTicker("INTC", "equity", "US"),
    UniverseTicker("CSCO", "equity", "US"),
    UniverseTicker("NFLX", "equity", "US"),
    UniverseTicker("DIS", "equity", "US"),
    UniverseTicker("T", "equity", "US"),
    UniverseTicker("VZ", "equity", "US"),
    UniverseTicker("V", "equity", "US"),
    UniverseTicker("MA", "equity", "US"),
    UniverseTicker("IWM", "etf", "US"),
    UniverseTicker("DIA", "etf", "US"),
    UniverseTicker("XLY", "etf", "US"),
    UniverseTicker("XLV", "etf", "US"),
    UniverseTicker("XLI", "etf", "US"),
    UniverseTicker("XLK", "etf", "US"),
    UniverseTicker("SMH", "etf", "US"),
    UniverseTicker("ARKK", "etf", "US"),
    UniverseTicker("TLT", "etf", "US"),
    UniverseTicker("GLD", "etf", "US"),
    UniverseTicker("SLV", "etf", "US"),
    UniverseTicker("USO", "etf", "US"),
    UniverseTicker("DOTUSD", "crypto", "GLOBAL"),
    UniverseTicker("XRPUSD", "crypto", "GLOBAL"),
    UniverseTicker("AVAXUSD", "crypto", "GLOBAL"),
    UniverseTicker("MATICUSD", "crypto", "GLOBAL"),
    UniverseTicker("LTCUSD", "crypto", "GLOBAL"),
]


class OpportunityScanner:
    def _prefilter(self, ticker: UniverseTicker) -> dict | None:
        df = load_mock_ohlcv(ticker.symbol, timeframe="1d", periods=100)
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
