import asyncio
import inspect
try:
    from app.core.config import settings
    from app.services.tradier_client import tradier_client
    from app.services.options_execution_service import options_execution_service
    from app.models.schemas import OptionsExecutionRequest
    
    STRATEGIES = [
        "LONG_CALL", "LONG_PUT", "VERTICAL_CALL", "VERTICAL_PUT", 
        "IRON_CONDOR", "STRADDLE", "STRANGLE", "COVERED_CALL"
    ]
except ImportError as e:
    print(f"Import Error: {e}")
    exit(1)

async def main():
    print("--- Tradier Runtime Status ---")
    print(f"configured: {tradier_client.is_configured()}")
    print(f"sandbox: {settings.tradier_sandbox}")
    print(f"live_enabled: {settings.tradier_live_trading_enabled}")
    print(f"active_key_present: {bool(settings.tradier_effective_api_key)}")
    print(f"active_account_present: {bool(settings.tradier_effective_account_number)}")
    print("------------------------------\n")

    results = []
    symbol = "SPY"
    quantity = 1

    for strategy in STRATEGIES:
        try:
            # Bias options: BULLISH, BEARISH, NEUTRAL
            bias = "BULLISH"
            if any(k in strategy.lower() for k in ["put", "bear"]):
                bias = "BEARISH"
            elif any(k in strategy.lower() for k in ["condor", "straddle", "strangle"]):
                bias = "NEUTRAL"

            request = OptionsExecutionRequest(
                symbol=symbol,
                strategy=strategy,
                quantity=quantity,
                bias=bias,
                preview=False
            )

            if inspect.iscoroutinefunction(options_execution_service.preview_or_execute):
                res = await options_execution_service.preview_or_execute(request)
            else:
                res = options_execution_service.preview_or_execute(request)

            data = res if isinstance(res, dict) else res.dict()
            results.append({
                "strategy": strategy,
                "approved": data.get("approved"),
                "order_class": data.get("order_class"),
                "legs_count": len(data.get("legs", [])),
                "risk_level": data.get("risk_level"),
                "reason": data.get("reason"),
                "order_response": data.get("order_response"),
                "exception": None
            })
        except Exception as e:
            results.append({
                "strategy": strategy,
                "exception": str(e)
            })

    print(f"{'Strategy':<15} | {'Appr':<5} | {'Class':<10} | {'Legs':<4} | {'Risk':<10} | {'Order ID/Status'}")
    print("-" * 105)
    
    counts = {"total": 0, "submitted": 0, "approved_not_submitted": 0, "blocked": 0, "exceptions": 0}
    
    for r in results:
        counts["total"] += 1
        if r.get("exception"):
            counts["exceptions"] += 1
            print(f"{r['strategy']:<15} | ERROR: {r['exception']}")
            continue
            
        strat = r["strategy"]
        appr = "Y" if r["approved"] else "N"
        oclass = r["order_class"] or "N/A"
        legs = r["legs_count"]
        risk = r["risk_level"] or "N/A"
        
        ord_resp = r.get("order_response")
        ord_info = "N/A"
        if ord_resp:
            if isinstance(ord_resp, dict):
                if "order" in ord_resp:
                    ord_info = f"ID: {ord_resp['order'].get('id')}"
                    counts["submitted"] += 1
                elif "errors" in ord_resp:
                    ord_info = f"ERR"
                else:
                    ord_info = "Present"
            else:
                ord_info = "Object"
        elif r["approved"]:
            ord_info = f"({r['reason']})" if r['reason'] else "(Approved - No Order)"
            counts["approved_not_submitted"] += 1
        else:
            ord_info = f"({r['reason']})" if r['reason'] else "(Blocked)"
            counts["blocked"] += 1

        print(f"{strat:<15} | {appr:<5} | {oclass:<10} | {legs:<4} | {risk:<10} | {ord_info}")

    print("\n--- Summary ---")
    print(f"Total: {counts['total']} | Submitted: {counts['submitted']} | Appr/NoSub: {counts['approved_not_submitted']} | Blocked: {counts['blocked']} | Errors: {counts['exceptions']}")

if __name__ == "__main__":
    asyncio.run(main())
