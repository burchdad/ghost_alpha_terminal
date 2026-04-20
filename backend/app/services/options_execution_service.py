from __future__ import annotations

from dataclasses import dataclass
import httpx

from app.core.config import settings
from app.models.schemas import (
    OptionContract,
    OptionsChainResponse,
    OptionsExecutionRequest,
    OptionsExecutionResponse,
    OptionsStrategyLegRequest,
    OptionsStrategyLegResponse,
    OptionsStrategyType,
    TradierOptionOrderRequest,
    TradierStrategyOrderRequest,
)
from app.services.options_risk_engine import options_risk_engine
from app.services.options_service import options_service
from app.services.tradier_client import tradier_client


@dataclass
class PlannedLeg:
    instrument: str
    action: str
    ratio: int
    quantity: int
    shares: int | None = None
    contract: OptionContract | None = None
    estimated_leg_value: float | None = None
    source: str = "manual"

    def to_response(self) -> OptionsStrategyLegResponse:
        return OptionsStrategyLegResponse(
            instrument=self.instrument,  # type: ignore[arg-type]
            action=self.action,
            ratio=self.ratio,
            quantity=self.quantity,
            shares=self.shares,
            option_symbol=self.contract.option_symbol if self.contract else None,
            option_type=self.contract.option_type if self.contract else None,
            strike=self.contract.strike if self.contract else None,
            expiration=self.contract.expiration if self.contract else None,
            bid=self.contract.bid if self.contract else None,
            ask=self.contract.ask if self.contract else None,
            last=self.contract.last if self.contract else None,
            mid=self.contract.mid if self.contract else None,
            estimated_leg_value=self.estimated_leg_value,
            source=self.source,  # type: ignore[arg-type]
        )


class OptionsExecutionService:
    def _normalize_strategy(self, request: OptionsExecutionRequest) -> OptionsStrategyType:
        if request.strategy:
            return request.strategy
        return "LONG_CALL" if request.bias == "BULLISH" else "LONG_PUT"

    def _load_chain(self, symbol: str, expiration: str | None) -> OptionsChainResponse:
        return options_service.get_options_chain(symbol=symbol, expiration=expiration)

    def _pick_secondary_expiration(self, primary: OptionsChainResponse, requested: str | None) -> str:
        expirations = primary.available_expirations or ([primary.selected_expiration] if primary.selected_expiration else [])
        if requested:
            return requested
        for expiration in expirations:
            if expiration and expiration != primary.selected_expiration:
                return expiration
        if primary.selected_expiration:
            return primary.selected_expiration
        raise ValueError("No secondary expiration available")

    def _default_width(self, underlying_price: float, requested_width: float | None) -> float:
        if requested_width is not None:
            return requested_width
        if underlying_price < 35:
            return 1.0
        if underlying_price < 80:
            return 2.5
        if underlying_price < 150:
            return 5.0
        return 10.0

    def _price_for_leg(self, contract: OptionContract, action: str) -> float:
        if action.startswith("buy"):
            return float(contract.ask or contract.mid or contract.last or 0.0)
        return float(contract.bid or contract.mid or contract.last or 0.0)

    def _eligible_contracts(
        self,
        chain: OptionsChainResponse,
        request: OptionsExecutionRequest,
        *,
        option_type: str,
        expiration: str | None = None,
    ) -> list[OptionContract]:
        result: list[OptionContract] = []
        relaxed_result: list[OptionContract] = []
        for contract in chain.contracts:
            if contract.option_type != option_type:
                continue
            if expiration and contract.expiration != expiration:
                continue
            price = contract.ask or contract.mid or contract.last or 0.0
            if price <= 0:
                continue
            relaxed_result.append(contract)
            spread_pct = 1.0
            if (contract.bid or 0.0) > 0 and (contract.ask or 0.0) > 0:
                spread_pct = ((contract.ask or 0.0) - (contract.bid or 0.0)) / max(price, 1e-6)
            if contract.open_interest < request.min_open_interest:
                continue
            if contract.volume < request.min_volume:
                continue
            if spread_pct > request.max_spread_pct:
                continue
            result.append(contract)
        if result:
            return result
        # If strict filters remove the whole chain (common in synthetic/illiquid data),
        # return a relaxed set so preview planning can still proceed.
        return relaxed_result

    def _choose_contract(
        self,
        contracts: list[OptionContract],
        *,
        target_strike: float,
        relation: str = "nearest",
    ) -> OptionContract:
        if not contracts:
            raise ValueError("No eligible contracts found for requested structure")
        if relation == "above":
            candidates = [contract for contract in contracts if contract.strike >= target_strike]
            if candidates:
                return min(candidates, key=lambda contract: (contract.strike - target_strike, -contract.open_interest, -contract.volume))
        if relation == "below":
            candidates = [contract for contract in contracts if contract.strike <= target_strike]
            if candidates:
                return min(candidates, key=lambda contract: (target_strike - contract.strike, -contract.open_interest, -contract.volume))
        return min(contracts, key=lambda contract: (abs(contract.strike - target_strike), -contract.open_interest, -contract.volume))

    def _leg_from_contract(self, contract: OptionContract, *, action: str, ratio: int, quantity: int) -> PlannedLeg:
        return PlannedLeg(
            instrument="option",
            action=action,
            ratio=ratio,
            quantity=quantity * ratio,
            contract=contract,
            estimated_leg_value=round(self._price_for_leg(contract, action) * 100 * quantity * ratio, 2),
            source=contract.source,
        )

    def _equity_leg(self, *, action: str, quantity: int, underlying_price: float) -> PlannedLeg:
        shares = quantity * 100
        return PlannedLeg(
            instrument="equity",
            action=action,
            ratio=1,
            quantity=quantity,
            shares=shares,
            estimated_leg_value=round(underlying_price * shares, 2),
            source="manual",
        )

    def _net_premium(self, legs: list[PlannedLeg]) -> tuple[float, float]:
        cash_flow = 0.0
        for leg in legs:
            value = leg.estimated_leg_value or 0.0
            if leg.action.startswith("buy"):
                cash_flow += value
            else:
                cash_flow -= value
        return round(max(cash_flow, 0.0), 2), round(max(-cash_flow, 0.0), 2)

    def _infer_order_class(self, legs: list[PlannedLeg]) -> str:
        option_legs = [leg for leg in legs if leg.instrument == "option"]
        equity_legs = [leg for leg in legs if leg.instrument == "equity"]
        if equity_legs and option_legs:
            return "combo"
        if len(option_legs) > 1:
            return "multileg"
        return "option"

    def _infer_order_type(self, order_class: str, net_debit: float, net_credit: float) -> str:
        if order_class == "option":
            return "limit" if (net_debit or net_credit) else "market"
        if net_debit > 0:
            return "debit"
        if net_credit > 0:
            return "credit"
        return "even"

    def _resolve_custom_leg(self, leg: OptionsStrategyLegRequest, request: OptionsExecutionRequest, chain: OptionsChainResponse) -> PlannedLeg:
        if leg.instrument == "equity":
            shares = leg.shares or request.quantity * 100 * leg.quantity_ratio
            return PlannedLeg(
                instrument="equity",
                action=leg.action,
                ratio=leg.quantity_ratio,
                quantity=request.quantity * leg.quantity_ratio,
                shares=shares,
                estimated_leg_value=round(chain.underlying_price * shares, 2),
                source="manual",
            )

        if leg.option_symbol:
            contract = next((item for item in chain.contracts if item.option_symbol == leg.option_symbol), None)
            if contract is None:
                raise ValueError(f"Custom option leg {leg.option_symbol} was not found in selected chain")
        else:
            if leg.option_type is None or leg.strike is None:
                raise ValueError("Custom option legs require option_type plus strike or option_symbol")
            eligible = self._eligible_contracts(chain, request, option_type=leg.option_type, expiration=leg.expiration or chain.selected_expiration)
            contract = self._choose_contract(eligible, target_strike=leg.strike)
        return self._leg_from_contract(contract, action=leg.action, ratio=leg.quantity_ratio, quantity=request.quantity)

    def build_strategy_plan(self, request: OptionsExecutionRequest) -> tuple[OptionsStrategyType, OptionsChainResponse, list[PlannedLeg], list[str]]:
        strategy = self._normalize_strategy(request)
        primary = self._load_chain(request.symbol, request.expiration)
        secondary_chain = None
        if strategy in {"CALENDAR_CALL", "CALENDAR_PUT", "DIAGONAL_CALL", "DIAGONAL_PUT"}:
            secondary_expiration = self._pick_secondary_expiration(primary, request.secondary_expiration)
            secondary_chain = self._load_chain(request.symbol, secondary_expiration)

        underlying = primary.underlying_price
        width = self._default_width(underlying, request.width)
        wing_width = self._default_width(underlying, request.wing_width or width)
        otm_pct = request.target_otm_pct or 0.03
        warnings: list[str] = []

        call_primary = self._eligible_contracts(primary, request, option_type="CALL", expiration=primary.selected_expiration)
        put_primary = self._eligible_contracts(primary, request, option_type="PUT", expiration=primary.selected_expiration)
        atm_call = self._choose_contract(call_primary, target_strike=underlying)
        atm_put = self._choose_contract(put_primary, target_strike=underlying)
        atm_strike = atm_call.strike if abs(atm_call.strike - underlying) <= abs(atm_put.strike - underlying) else atm_put.strike

        def choose(option_type: str, target: float, relation: str = "nearest", chain: OptionsChainResponse | None = None) -> OptionContract:
            active_chain = chain or primary
            eligible = self._eligible_contracts(active_chain, request, option_type=option_type, expiration=active_chain.selected_expiration)
            return self._choose_contract(eligible, target_strike=target, relation=relation)

        legs: list[PlannedLeg]
        if strategy == "LONG_CALL":
            legs = [self._leg_from_contract(atm_call, action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "LONG_PUT":
            legs = [self._leg_from_contract(atm_put, action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "VERTICAL_CALL":
            outer = choose("CALL", atm_strike + width, relation="above")
            if request.bias == "BEARISH":
                legs = [self._leg_from_contract(atm_call, action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(outer, action="buy_to_open", ratio=1, quantity=request.quantity)]
            else:
                legs = [self._leg_from_contract(atm_call, action="buy_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(outer, action="sell_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "VERTICAL_PUT":
            lower = choose("PUT", atm_strike - width, relation="below")
            if request.bias == "BULLISH":
                legs = [self._leg_from_contract(atm_put, action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(lower, action="buy_to_open", ratio=1, quantity=request.quantity)]
            else:
                legs = [self._leg_from_contract(atm_put, action="buy_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(lower, action="sell_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "CALENDAR_CALL":
            if secondary_chain is None:
                raise ValueError("Calendar call requires a secondary expiration")
            legs = [self._leg_from_contract(choose("CALL", atm_strike, chain=primary), action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("CALL", atm_strike, chain=secondary_chain), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "CALENDAR_PUT":
            if secondary_chain is None:
                raise ValueError("Calendar put requires a secondary expiration")
            legs = [self._leg_from_contract(choose("PUT", atm_strike, chain=primary), action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("PUT", atm_strike, chain=secondary_chain), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "DIAGONAL_CALL":
            if secondary_chain is None:
                raise ValueError("Diagonal call requires a secondary expiration")
            legs = [self._leg_from_contract(choose("CALL", atm_strike + width, relation="above", chain=primary), action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("CALL", atm_strike, chain=secondary_chain), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "DIAGONAL_PUT":
            if secondary_chain is None:
                raise ValueError("Diagonal put requires a secondary expiration")
            legs = [self._leg_from_contract(choose("PUT", atm_strike - width, relation="below", chain=primary), action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("PUT", atm_strike, chain=secondary_chain), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "RATIO_CALL":
            legs = [self._leg_from_contract(atm_call, action="buy_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("CALL", atm_strike + width, relation="above"), action="sell_to_open", ratio=2, quantity=request.quantity)]
            warnings.append("Ratio call spread uses a 1x2 structure and can create uncovered upside risk.")
        elif strategy == "RATIO_PUT":
            legs = [self._leg_from_contract(atm_put, action="buy_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("PUT", atm_strike - width, relation="below"), action="sell_to_open", ratio=2, quantity=request.quantity)]
            warnings.append("Ratio put spread uses a 1x2 structure and can create uncovered downside risk.")
        elif strategy == "BUTTERFLY_CALL":
            legs = [self._leg_from_contract(choose("CALL", atm_strike - width, relation="below"), action="buy_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("CALL", atm_strike), action="sell_to_open", ratio=2, quantity=request.quantity), self._leg_from_contract(choose("CALL", atm_strike + width, relation="above"), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "BUTTERFLY_PUT":
            legs = [self._leg_from_contract(choose("PUT", atm_strike - width, relation="below"), action="buy_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("PUT", atm_strike), action="sell_to_open", ratio=2, quantity=request.quantity), self._leg_from_contract(choose("PUT", atm_strike + width, relation="above"), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "CONDOR_CALL":
            legs = [self._leg_from_contract(choose("CALL", atm_strike - width, relation="below"), action="buy_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("CALL", atm_strike), action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("CALL", atm_strike + width, relation="above"), action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("CALL", atm_strike + width + wing_width, relation="above"), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "CONDOR_PUT":
            legs = [self._leg_from_contract(choose("PUT", atm_strike - width - wing_width, relation="below"), action="buy_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("PUT", atm_strike - width, relation="below"), action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("PUT", atm_strike), action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("PUT", atm_strike + width, relation="above"), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "IRON_CONDOR":
            legs = [self._leg_from_contract(choose("PUT", atm_strike - width - wing_width, relation="below"), action="buy_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("PUT", atm_strike - width, relation="below"), action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("CALL", atm_strike + width, relation="above"), action="sell_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("CALL", atm_strike + width + wing_width, relation="above"), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "STRADDLE":
            legs = [self._leg_from_contract(atm_call, action="buy_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(atm_put, action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "STRANGLE":
            legs = [self._leg_from_contract(choose("CALL", underlying * (1 + otm_pct), relation="above"), action="buy_to_open", ratio=1, quantity=request.quantity), self._leg_from_contract(choose("PUT", underlying * (1 - otm_pct), relation="below"), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "COVERED_CALL":
            legs = [self._equity_leg(action="buy", quantity=request.quantity, underlying_price=underlying), self._leg_from_contract(choose("CALL", underlying * (1 + otm_pct), relation="above"), action="sell_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "COVERED_PUT":
            legs = [self._equity_leg(action="sell", quantity=request.quantity, underlying_price=underlying), self._leg_from_contract(choose("PUT", underlying * (1 - otm_pct), relation="below"), action="sell_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "PROTECTIVE_CALL":
            legs = [self._equity_leg(action="sell", quantity=request.quantity, underlying_price=underlying), self._leg_from_contract(choose("CALL", underlying * (1 + otm_pct), relation="above"), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy == "PROTECTIVE_PUT":
            legs = [self._equity_leg(action="buy", quantity=request.quantity, underlying_price=underlying), self._leg_from_contract(choose("PUT", underlying * (1 - otm_pct), relation="below"), action="buy_to_open", ratio=1, quantity=request.quantity)]
        elif strategy in {"CUSTOM_2_LEG", "CUSTOM_3_LEG", "CUSTOM_4_LEG", "CUSTOM_STOCK_OPTION"}:
            supplied_legs = list(request.custom_legs)

            # Provide sensible templates when custom legs are omitted so preview flows
            # can still exercise all custom strategy routes.
            if not supplied_legs:
                if strategy == "CUSTOM_2_LEG":
                    supplied_legs = [
                        OptionsStrategyLegRequest(instrument="option", option_type="CALL", action="buy_to_open", strike=atm_strike, expiration=primary.selected_expiration, quantity_ratio=1),
                        OptionsStrategyLegRequest(instrument="option", option_type="CALL", action="sell_to_open", strike=atm_strike + width, expiration=primary.selected_expiration, quantity_ratio=1),
                    ]
                    warnings.append("CUSTOM_2_LEG used default 2-leg call spread template because no legs were provided.")
                elif strategy == "CUSTOM_3_LEG":
                    supplied_legs = [
                        OptionsStrategyLegRequest(instrument="option", option_type="CALL", action="buy_to_open", strike=atm_strike - width, expiration=primary.selected_expiration, quantity_ratio=1),
                        OptionsStrategyLegRequest(instrument="option", option_type="CALL", action="sell_to_open", strike=atm_strike, expiration=primary.selected_expiration, quantity_ratio=2),
                        OptionsStrategyLegRequest(instrument="option", option_type="CALL", action="buy_to_open", strike=atm_strike + width, expiration=primary.selected_expiration, quantity_ratio=1),
                    ]
                    warnings.append("CUSTOM_3_LEG used default butterfly template because no legs were provided.")
                elif strategy == "CUSTOM_4_LEG":
                    supplied_legs = [
                        OptionsStrategyLegRequest(instrument="option", option_type="PUT", action="buy_to_open", strike=atm_strike - width - wing_width, expiration=primary.selected_expiration, quantity_ratio=1),
                        OptionsStrategyLegRequest(instrument="option", option_type="PUT", action="sell_to_open", strike=atm_strike - width, expiration=primary.selected_expiration, quantity_ratio=1),
                        OptionsStrategyLegRequest(instrument="option", option_type="CALL", action="sell_to_open", strike=atm_strike + width, expiration=primary.selected_expiration, quantity_ratio=1),
                        OptionsStrategyLegRequest(instrument="option", option_type="CALL", action="buy_to_open", strike=atm_strike + width + wing_width, expiration=primary.selected_expiration, quantity_ratio=1),
                    ]
                    warnings.append("CUSTOM_4_LEG used default iron condor template because no legs were provided.")
                elif strategy == "CUSTOM_STOCK_OPTION":
                    supplied_legs = [
                        OptionsStrategyLegRequest(instrument="equity", action="buy", shares=request.quantity * 100, quantity_ratio=1),
                        OptionsStrategyLegRequest(instrument="option", option_type="PUT", action="buy_to_open", strike=underlying * (1 - otm_pct), expiration=primary.selected_expiration, quantity_ratio=1),
                    ]
                    warnings.append("CUSTOM_STOCK_OPTION used default protective stock+put template because no legs were provided.")

            expected = {"CUSTOM_2_LEG": 2, "CUSTOM_3_LEG": 3, "CUSTOM_4_LEG": 4}.get(strategy)
            if expected is not None and len(supplied_legs) != expected:
                raise ValueError(f"{strategy} requires exactly {expected} custom legs")
            if strategy == "CUSTOM_STOCK_OPTION" and not any(leg.instrument == "equity" for leg in supplied_legs):
                raise ValueError("CUSTOM_STOCK_OPTION requires at least one equity leg")
            legs = [self._resolve_custom_leg(leg, request, primary) for leg in supplied_legs]
        else:
            raise ValueError(f"Unsupported strategy {strategy}")

        return strategy, primary, legs, warnings

    def _response_from_plan(
        self,
        *,
        request: OptionsExecutionRequest,
        strategy: OptionsStrategyType,
        primary: OptionsChainResponse,
        legs: list[PlannedLeg],
        reason: str,
        order_preview: bool,
        order_response: dict | None = None,
        warnings: list[str] | None = None,
    ) -> OptionsExecutionResponse:
        net_debit, net_credit = self._net_premium(legs)
        response_legs = [leg.to_response() for leg in legs]
        risk = options_risk_engine.evaluate_strategy(
            strategy=strategy,
            legs=response_legs,
            quantity=request.quantity,
            account_balance=request.account_balance,
            confidence=request.confidence,
            underlying_price=primary.underlying_price,
            net_debit=net_debit,
            net_credit=net_credit,
            max_spread_pct=request.max_spread_pct,
        )
        first_option_leg = next((leg for leg in response_legs if leg.instrument == "option"), None)
        return OptionsExecutionResponse(
            approved=risk.approved,
            symbol=request.symbol.upper(),
            strategy=strategy,
            order_class=self._infer_order_class(legs),
            option_symbol=first_option_leg.option_symbol if first_option_leg else None,
            side=first_option_leg.action if first_option_leg else None,
            quantity=request.quantity,
            expiration=primary.selected_expiration,
            secondary_expiration=request.secondary_expiration,
            bid=first_option_leg.bid if first_option_leg else None,
            ask=first_option_leg.ask if first_option_leg else None,
            last=first_option_leg.last if first_option_leg else None,
            mid=first_option_leg.mid if first_option_leg else None,
            estimated_cost=net_debit or net_credit,
            estimated_net_debit=net_debit or None,
            estimated_net_credit=net_credit or None,
            order_preview=order_preview,
            order_response=order_response,
            risk=risk,
            legs=response_legs,
            warnings=(warnings or []) + list(risk.warnings),
            reason=reason if risk.approved else risk.reason,
        )

    def submit_tradier_option_order(self, payload: TradierOptionOrderRequest) -> dict:
        body: dict[str, str] = {
            "class": "option",
            # Tradier expects underlying in symbol and full OCC contract in option_symbol.
            "symbol": payload.underlying.upper(),
            "option_symbol": payload.option_symbol,
            "side": payload.side,
            "quantity": str(payload.quantity),
            "type": payload.order_type,
            "duration": payload.duration,
            "tag": payload.tag or f"{payload.underlying.upper()}-options-sprint",
        }
        if payload.order_type in {"limit", "stop_limit"}:
            if payload.price is None:
                raise ValueError("price is required for limit and stop_limit option orders")
            body["price"] = str(payload.price)
        if payload.order_type in {"stop", "stop_limit"}:
            if payload.stop is None:
                raise ValueError("stop is required for stop and stop_limit option orders")
            body["stop"] = str(payload.stop)
        if payload.preview:
            body["preview"] = "true"
        return tradier_client.post_form(f"/accounts/{settings.tradier_effective_account_number}/orders", data=body)

    def submit_tradier_strategy_order(self, payload: TradierStrategyOrderRequest) -> dict:
        body: dict[str, str] = {
            "class": payload.order_class,
            "symbol": payload.underlying.upper(),
            "type": payload.order_type,
            "duration": payload.duration,
            "quantity": str(payload.quantity),
            "tag": payload.tag or f"{payload.underlying.upper()}-{payload.strategy.lower().replace('_', '-')}",
        }
        if payload.price is not None:
            body["price"] = str(payload.price)
        if payload.stop is not None:
            body["stop"] = str(payload.stop)
        if payload.preview:
            body["preview"] = "true"
        for idx, leg in enumerate(payload.legs):
            if leg.instrument == "equity":
                body[f"symbol[{idx}]"] = payload.underlying.upper()
                body[f"side[{idx}]"] = leg.action
                body[f"quantity[{idx}]"] = str(leg.shares or payload.quantity * 100 * leg.quantity_ratio)
            else:
                if not leg.option_symbol:
                    raise ValueError("Strategy option legs require option_symbol")
                body[f"option_symbol[{idx}]"] = leg.option_symbol
                body[f"side[{idx}]"] = leg.action
                body[f"quantity[{idx}]"] = str(payload.quantity * leg.quantity_ratio)
        return tradier_client.post_form(f"/accounts/{settings.tradier_effective_account_number}/orders", data=body)

    def select_contract(self, request: OptionsExecutionRequest) -> OptionContract | None:
        strategy, _primary, legs, _warnings = self.build_strategy_plan(request)
        if strategy not in {"LONG_CALL", "LONG_PUT"}:
            return next((leg.contract for leg in legs if leg.contract is not None), None)
        return next((leg.contract for leg in legs if leg.contract is not None), None)

    def preview_or_execute(self, request: OptionsExecutionRequest) -> OptionsExecutionResponse:
        strategy, primary, legs, warnings = self.build_strategy_plan(request)
        preview_response = self._response_from_plan(
            request=request,
            strategy=strategy,
            primary=primary,
            legs=legs,
            reason="Strategy plan generated and approved for preview.",
            order_preview=request.preview,
            warnings=warnings,
        )
        if request.preview or not preview_response.approved:
            return preview_response
        if not tradier_client.is_configured():
            return preview_response.model_copy(update={"approved": False, "reason": "Tradier active credentials are not configured."})
        if not settings.tradier_live_trading_enabled:
            return preview_response.model_copy(update={"approved": False, "reason": "Tradier live trading is disabled by configuration."})

        net_debit = preview_response.estimated_net_debit or 0.0
        net_credit = preview_response.estimated_net_credit or 0.0
        order_class = preview_response.order_class or self._infer_order_class(legs)
        order_type = self._infer_order_type(order_class, net_debit=net_debit, net_credit=net_credit)

        if order_class == "option" and len(preview_response.legs) == 1 and preview_response.option_symbol and preview_response.side:
            order_response = self.submit_tradier_option_order(
                TradierOptionOrderRequest(
                    underlying=request.symbol.upper(),
                    option_symbol=preview_response.option_symbol,
                    side=preview_response.side,  # type: ignore[arg-type]
                    quantity=request.quantity,
                    order_type="limit" if (preview_response.ask or preview_response.mid) else "market",
                    duration="day",
                    price=preview_response.ask or preview_response.mid,
                    preview=False,
                )
            )
        else:
            order_response = self.submit_tradier_strategy_order(
                TradierStrategyOrderRequest(
                    underlying=request.symbol.upper(),
                    strategy=strategy,
                    order_class=order_class,  # type: ignore[arg-type]
                    order_type=order_type,  # type: ignore[arg-type]
                    duration="day",
                    quantity=request.quantity,
                    price=round(net_debit or net_credit, 2) if order_type in {"debit", "credit"} else None,
                    preview=False,
                    legs=[
                        OptionsStrategyLegRequest(
                            instrument=leg.instrument,  # type: ignore[arg-type]
                            option_symbol=leg.option_symbol,
                            option_type=leg.option_type,
                            action=leg.action,  # type: ignore[arg-type]
                            strike=leg.strike,
                            expiration=leg.expiration,
                            quantity_ratio=leg.ratio,
                            shares=leg.shares,
                        )
                        for leg in preview_response.legs
                    ],
                )
            )
        return preview_response.model_copy(update={"order_preview": False, "order_response": order_response, "reason": f"Tradier {strategy.lower()} order submitted."})


options_execution_service = OptionsExecutionService()