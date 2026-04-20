from __future__ import annotations

import os
import sys
import unittest
from unittest.mock import patch


sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


from app.models.schemas import OptionsExecutionRequest  # noqa: E402
from app.models.schemas import OptionsStrategyLegRequest, TradierOptionOrderRequest, TradierStrategyOrderRequest  # noqa: E402
from app.services.options_execution_service import options_execution_service  # noqa: E402


class TestOptionsStrategyExecution(unittest.TestCase):
    def test_vertical_call_preview_builds_two_leg_multileg_plan(self):
        response = options_execution_service.preview_or_execute(
            OptionsExecutionRequest(
                symbol="AAPL",
                strategy="VERTICAL_CALL",
                bias="BULLISH",
                quantity=1,
                preview=True,
            )
        )

        self.assertEqual(response.strategy, "VERTICAL_CALL")
        self.assertEqual(response.order_class, "multileg")
        self.assertEqual(len(response.legs), 2)
        self.assertTrue(all(leg.instrument == "option" for leg in response.legs))
        self.assertEqual(response.legs[0].action, "buy_to_open")
        self.assertEqual(response.legs[1].action, "sell_to_open")
        self.assertIsNotNone(response.risk)

    def test_straddle_preview_builds_call_and_put(self):
        response = options_execution_service.preview_or_execute(
            OptionsExecutionRequest(
                symbol="SPY",
                strategy="STRADDLE",
                bias="NEUTRAL",
                quantity=1,
                preview=True,
            )
        )

        self.assertEqual(response.strategy, "STRADDLE")
        self.assertEqual(response.order_class, "multileg")
        self.assertEqual(len(response.legs), 2)
        self.assertEqual({leg.option_type for leg in response.legs}, {"CALL", "PUT"})
        self.assertTrue(all(leg.action == "buy_to_open" for leg in response.legs))

    def test_covered_call_preview_builds_combo_order(self):
        response = options_execution_service.preview_or_execute(
            OptionsExecutionRequest(
                symbol="MSFT",
                strategy="COVERED_CALL",
                bias="BULLISH",
                quantity=1,
                preview=True,
            )
        )

        self.assertEqual(response.strategy, "COVERED_CALL")
        self.assertEqual(response.order_class, "combo")
        self.assertEqual(len(response.legs), 2)
        self.assertEqual(response.legs[0].instrument, "equity")
        self.assertEqual(response.legs[1].instrument, "option")
        self.assertEqual(response.legs[1].action, "sell_to_open")

    def test_tradier_strategy_payload_contains_indexed_leg_fields(self):
        scenarios = [
            ("VERTICAL_CALL", "AAPL", "BULLISH", "multileg", 2),
            ("IRON_CONDOR", "SPY", "NEUTRAL", "multileg", 4),
            ("COVERED_CALL", "MSFT", "BULLISH", "combo", 2),
        ]

        captured_calls: list[dict] = []

        def _capture_post_form(endpoint: str, data: dict):
            captured_calls.append({"endpoint": endpoint, "data": dict(data)})
            return {"order": {"id": 123, "status": "ok"}}

        with patch("app.services.options_execution_service.tradier_client.post_form", side_effect=_capture_post_form):
            for strategy, symbol, bias, expected_class, expected_legs in scenarios:
                preview = options_execution_service.preview_or_execute(
                    OptionsExecutionRequest(
                        symbol=symbol,
                        strategy=strategy,
                        bias=bias,
                        quantity=1,
                        preview=True,
                    )
                )

                net_debit = preview.estimated_net_debit or 0.0
                net_credit = preview.estimated_net_credit or 0.0
                order_class = preview.order_class or expected_class
                order_type = options_execution_service._infer_order_type(order_class, net_debit=net_debit, net_credit=net_credit)  # noqa: SLF001

                request = TradierStrategyOrderRequest(
                    underlying=symbol,
                    strategy=strategy,
                    order_class=order_class,
                    order_type=order_type,
                    duration="day",
                    quantity=1,
                    price=round(net_debit or net_credit, 2) if order_type in {"debit", "credit"} else None,
                    preview=True,
                    legs=[
                        OptionsStrategyLegRequest(
                            instrument=leg.instrument,
                            option_symbol=leg.option_symbol,
                            option_type=leg.option_type,
                            action=leg.action,
                            strike=leg.strike,
                            expiration=leg.expiration,
                            quantity_ratio=leg.ratio,
                            shares=leg.shares,
                        )
                        for leg in preview.legs
                    ],
                )
                options_execution_service.submit_tradier_strategy_order(request)

                call = captured_calls[-1]
                body = call["data"]
                self.assertEqual(body["class"], expected_class)
                self.assertEqual(body["symbol"], symbol)
                self.assertEqual(body["preview"], "true")
                side_keys = [key for key in body if key.startswith("side[")]
                quantity_keys = [key for key in body if key.startswith("quantity[")]
                self.assertEqual(len(side_keys), expected_legs)
                self.assertEqual(len(quantity_keys), expected_legs)
                self.assertTrue(any(key.startswith("option_symbol[") for key in body))
                if expected_class == "combo":
                    self.assertTrue(any(key.startswith("symbol[") for key in body))


    def test_tradier_single_leg_option_payload_uses_underlying_symbol(self):
        captured: dict[str, dict] = {}

        def _capture_post_form(endpoint: str, data: dict):
            captured["endpoint"] = endpoint
            captured["data"] = dict(data)
            return {"order": {"id": 999, "status": "ok"}}

        with patch("app.services.options_execution_service.tradier_client.post_form", side_effect=_capture_post_form):
            options_execution_service.submit_tradier_option_order(
                TradierOptionOrderRequest(
                    underlying="SPY",
                    option_symbol="SPY260619C00500000",
                    side="buy_to_open",
                    quantity=1,
                    order_type="limit",
                    duration="day",
                    price=1.23,
                    preview=False,
                )
            )

        body = captured["data"]
        self.assertEqual(body["class"], "option")
        self.assertEqual(body["symbol"], "SPY")
        self.assertEqual(body["option_symbol"], "SPY260619C00500000")
        self.assertEqual(body["side"], "buy_to_open")
        self.assertEqual(body["type"], "limit")


if __name__ == "__main__":
    unittest.main()