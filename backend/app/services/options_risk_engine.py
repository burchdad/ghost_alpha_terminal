from __future__ import annotations

from app.models.schemas import OptionsRiskAssessmentResponse, OptionsStrategyLegResponse, OptionsStrategyType


class OptionsRiskEngine:
    def _average_spread_pct(self, legs: list[OptionsStrategyLegResponse]) -> float:
        spreads: list[float] = []
        for leg in legs:
            if leg.instrument != "option":
                continue
            bid = leg.bid or 0.0
            ask = leg.ask or 0.0
            basis = leg.mid or leg.last or ask or bid
            if bid > 0 and ask > 0 and basis > 0:
                spreads.append(max((ask - bid) / basis, 0.0))
        return round(sum(spreads) / len(spreads), 4) if spreads else 0.0

    def _infer_width(self, legs: list[OptionsStrategyLegResponse], option_type: str | None = None) -> float:
        strikes = sorted(
            {float(leg.strike) for leg in legs if leg.instrument == "option" and leg.strike is not None and (option_type is None or leg.option_type == option_type)}
        )
        if len(strikes) < 2:
            return 0.0
        diffs = [round(strikes[idx + 1] - strikes[idx], 4) for idx in range(len(strikes) - 1)]
        return max(diffs) if diffs else 0.0

    def _strategy_caps(self, strategy: OptionsStrategyType) -> tuple[float, float]:
        if strategy in {"COVERED_CALL", "PROTECTIVE_PUT", "PROTECTIVE_CALL"}:
            return 0.25, 0.08
        if strategy in {"COVERED_PUT", "RATIO_CALL", "RATIO_PUT", "CUSTOM_STOCK_OPTION"}:
            return 0.35, 0.12
        return 0.10, 0.05

    def evaluate_strategy(
        self,
        *,
        strategy: OptionsStrategyType,
        legs: list[OptionsStrategyLegResponse],
        quantity: int,
        account_balance: float,
        confidence: float,
        underlying_price: float,
        net_debit: float,
        net_credit: float,
        max_spread_pct: float,
    ) -> OptionsRiskAssessmentResponse:
        spread_pct = self._average_spread_pct(legs)
        contract_cost = round(net_debit if net_debit > 0 else net_credit, 2)
        warnings: list[str] = []

        max_profit_amount: float | None = None
        if strategy in {"LONG_CALL", "LONG_PUT", "CALENDAR_CALL", "CALENDAR_PUT", "DIAGONAL_CALL", "DIAGONAL_PUT", "STRADDLE", "STRANGLE", "BUTTERFLY_CALL", "BUTTERFLY_PUT", "CONDOR_CALL", "CONDOR_PUT"}:
            max_loss_amount = round(net_debit, 2)
        elif strategy in {"VERTICAL_CALL", "VERTICAL_PUT"}:
            width = self._infer_width(legs)
            spread_value = width * 100 * quantity
            if net_debit > 0:
                max_loss_amount = round(net_debit, 2)
                max_profit_amount = round(max(spread_value - net_debit, 0.0), 2)
            else:
                max_loss_amount = round(max(spread_value - net_credit, 0.0), 2)
                max_profit_amount = round(net_credit, 2)
        elif strategy == "IRON_CONDOR":
            width = max(self._infer_width(legs, "CALL"), self._infer_width(legs, "PUT"))
            spread_value = width * 100 * quantity
            max_loss_amount = round(max(spread_value - net_credit, 0.0), 2)
            max_profit_amount = round(net_credit, 2)
        elif strategy in {"RATIO_CALL", "RATIO_PUT"}:
            max_loss_amount = round(max(net_debit, account_balance * 0.12), 2)
            warnings.append("Ratio spreads can have undefined or highly asymmetric risk beyond the modeled strike range.")
        elif strategy == "COVERED_CALL":
            stock_cost = underlying_price * 100 * quantity
            short_calls = [leg for leg in legs if leg.instrument == "option" and leg.action.startswith("sell") and leg.strike is not None]
            call_strike = float(short_calls[0].strike) if short_calls else underlying_price
            max_loss_amount = round(max(stock_cost - net_credit, 0.0), 2)
            max_profit_amount = round(max((call_strike - underlying_price) * 100 * quantity + net_credit, 0.0), 2)
        elif strategy == "COVERED_PUT":
            max_loss_amount = round(account_balance * 0.20, 2)
            warnings.append("Covered puts depend on short stock borrow and carry; downside is capped but upside risk remains large.")
        elif strategy == "PROTECTIVE_PUT":
            puts = [leg for leg in legs if leg.instrument == "option" and leg.option_type == "PUT" and leg.strike is not None]
            floor_strike = float(puts[0].strike) if puts else underlying_price
            max_loss_amount = round(max((underlying_price - floor_strike) * 100 * quantity + net_debit, 0.0), 2)
        elif strategy == "PROTECTIVE_CALL":
            calls = [leg for leg in legs if leg.instrument == "option" and leg.option_type == "CALL" and leg.strike is not None]
            cap_strike = float(calls[0].strike) if calls else underlying_price
            max_loss_amount = round(max((cap_strike - underlying_price) * 100 * quantity + net_debit, 0.0), 2)
        else:
            max_loss_amount = round(max(net_debit, account_balance * 0.08), 2)
            warnings.append("Custom strategy risk is estimated conservatively from net premium and structure width.")

        if max_profit_amount is None:
            if strategy in {"STRADDLE", "STRANGLE", "LONG_CALL", "LONG_PUT", "CALENDAR_CALL", "CALENDAR_PUT", "DIAGONAL_CALL", "DIAGONAL_PUT", "RATIO_CALL", "RATIO_PUT", "PROTECTIVE_CALL", "PROTECTIVE_PUT"}:
                max_profit_amount = None
            elif net_credit > 0:
                max_profit_amount = round(net_credit, 2)

        max_loss_pct = round((max_loss_amount / account_balance) if account_balance > 0 else 1.0, 4)
        loss_cap_pct, warning_cap_pct = self._strategy_caps(strategy)

        expected_gain = (max_profit_amount if max_profit_amount is not None else max_loss_amount * 1.4) * min(max(confidence, 0.2), 0.92)
        expected_loss = max_loss_amount * max(0.18, 1.0 - confidence)
        expected_value = round(expected_gain - expected_loss, 2)
        risk_reward_ratio = round((expected_gain / expected_loss) if expected_loss > 0 else 0.0, 2)

        blockers: list[str] = []
        if spread_pct > max_spread_pct:
            blockers.append(f"Average option spread {spread_pct:.1%} exceeds limit {max_spread_pct:.1%}.")
        if max_loss_pct > loss_cap_pct:
            blockers.append(f"Estimated max loss is {max_loss_pct:.1%} of account balance; cap for {strategy} is {loss_cap_pct:.1%}.")
        elif max_loss_pct > warning_cap_pct:
            warnings.append(f"Estimated max loss is elevated at {max_loss_pct:.1%} of account balance.")

        risk_level = "LOW"
        if spread_pct > 0.12 or max_loss_pct > warning_cap_pct or strategy in {"RATIO_CALL", "RATIO_PUT", "COVERED_PUT"}:
            risk_level = "HIGH"
        elif spread_pct > 0.06 or max_loss_pct > warning_cap_pct * 0.55:
            risk_level = "MEDIUM"

        return OptionsRiskAssessmentResponse(
            approved=not blockers,
            risk_level=risk_level,
            risk_reward_ratio=risk_reward_ratio,
            expected_value=expected_value,
            max_loss_amount=max_loss_amount,
            max_profit_amount=max_profit_amount,
            max_loss_pct_of_balance=max_loss_pct,
            spread_pct=spread_pct,
            contracts=quantity,
            contract_cost=contract_cost,
            stop_loss_pct=0.45,
            take_profit_pct=0.85,
            reason="Strategy passed structure and risk checks." if not blockers else " ".join(blockers),
            warnings=warnings,
        )

options_risk_engine = OptionsRiskEngine()