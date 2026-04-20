import requests
import json
import time

base_url = "https://ghostalphaterminal-production.up.railway.app"

strategies = [
    "LONG_CALL", "LONG_PUT", "VERTICAL_CALL", "VERTICAL_PUT", "CALENDAR_CALL", "CALENDAR_PUT", 
    "DIAGONAL_CALL", "DIAGONAL_PUT", "RATIO_CALL", "RATIO_PUT", "BUTTERFLY_CALL", "BUTTERFLY_PUT", 
    "CONDOR_CALL", "CONDOR_PUT", "IRON_CONDOR", "STRADDLE", "STRANGLE", "COVERED_CALL", 
    "COVERED_PUT", "PROTECTIVE_CALL", "PROTECTIVE_PUT", "CUSTOM_2_LEG", "CUSTOM_3_LEG", 
    "CUSTOM_4_LEG", "CUSTOM_STOCK_OPTION"
]

def get_bias(strategy):
    neutral = ["IRON_CONDOR", "STRADDLE", "STRANGLE"]
    if any(s in strategy for s in ["BUTTERFLY", "CONDOR"]) or strategy in neutral:
        return "NEUTRAL"
    if "PUT" in strategy:
        return "BEARISH"
    return "BULLISH"

def run_strategy(strat):
    bias = get_bias(strat)
    payload = {
        "symbol": "SPY",
        "strategy": strat,
        "quantity": 1,
        "preview": False,
        "bias": bias
    }
    
    # Simple retry / backoff for 429
    for attempt in range(3):
        try:
            r = requests.post(f"{base_url}/options/execute", json=payload, timeout=20)
            if r.status_code == 429:
                time.sleep(2 * (attempt + 1))
                continue
            
            status = r.status_code
            try:
                data = r.json()
            except:
                data = {"detail": r.text}
            return {
                "strategy": strat,
                "status": status,
                "approved": data.get("approved"),
                "order_preview": "Yes" if "order_preview" in data else "No",
                "legs": len(data.get("legs", [])) if isinstance(data.get("legs"), list) else 0,
                "reason": data.get("reason"),
                "detail": data.get("detail"),
                "order_response_present": "order_response" in data
            }
        except Exception as e:
            return {"strategy": strat, "status": "Error", "detail": str(e)}
    return {"strategy": strat, "status": 429, "detail": "Rate limit exceeded after retries"}

if __name__ == "__main__":
    print("--- 1) Health and Config Check ---")
    for endpoint in ["/health", "/tradier/config-check"]:
        try:
            r = requests.get(f"{base_url}{endpoint}", timeout=10)
            print(f"GET {endpoint} - Status: {r.status_code}")
            try:
                print(f"JSON: {json.dumps(r.json(), indent=2)}")
            except:
                print(f"Text: {r.text[:100]}")
        except Exception as e:
            print(f"GET {endpoint} failed: {e}")
    print()

    print("--- 2-3) Execution Strategy Test ---")
    results = []
    # Running sequentially with delay to avoid 429
    for strat in strategies:
        results.append(run_strategy(strat))
        time.sleep(1)

    print(f"{'Strategy':<20} | {'Status':<6} | {'Appr':<5} | {'Prev':<5} | {'Legs':<4} | {'Reason/Detail'}")
    print("-" * 100)
    
    status_counts = {}
    outcome_counts = {"approved": 0, "blocked": 0, "submitted": 0, "other": 0}
    auth_blocked_body = None

    for r in results:
        status = r.get("status")
        status_counts[status] = status_counts.get(status, 0) + 1
        
        reason_detail = str(r.get('reason') or r.get('detail') or "")
        print(f"{r['strategy']:<20} | {str(status):<6} | {str(r.get('approved')):<5} | {str(r.get('order_preview')):<5} | {str(r.get('legs')):<4} | {reason_detail}")
        
        if r.get("approved") is True:
            outcome_counts["approved"] += 1
        elif r.get("approved") is False:
            outcome_counts["blocked"] += 1
        
        if r.get("order_response_present"):
            outcome_counts["submitted"] += 1
        
        if not any([r.get("approved") is True, r.get("approved") is False, r.get("order_response_present")]):
            outcome_counts["other"] += 1

        if status in [401, 403, 429] and not auth_blocked_body:
            auth_blocked_body = reason_detail

    print("\n--- 4) Summary ---")
    print(f"By Status: {status_counts}")
    print(f"By Outcome: {outcome_counts}")

    if auth_blocked_body:
        print(f"\n--- 5) Blocked Detected ---")
        print(f"Representative response: {auth_blocked_body}")
