import requests
import json

BASE_URL = "https://ghostalphaterminal-production.up.railway.app"

def test_api():
    print(f"Testing {BASE_URL}")
    
    # 1) GET /health and /openapi.json
    try:
        health_resp = requests.get(f"{BASE_URL}/health")
        print(f"GET /health status: {health_resp.status_code}")
    except Exception as e:
        print(f"GET /health failed: {e}")

    openapi_data = None
    try:
        openapi_resp = requests.get(f"{BASE_URL}/openapi.json")
        print(f"GET /openapi.json status: {openapi_resp.status_code}")
        if openapi_resp.status_code == 200:
            openapi_data = openapi_resp.json()
    except Exception as e:
        print(f"GET /openapi.json failed: {e}")

    if not openapi_data:
        print("Could not retrieve openapi.json, aborting.")
        return

    # 2) Confirm paths
    paths_to_check = ["/options/execute", "/tradier/config-check", "/tradier/options/strategy-orders"]
    existing_paths = openapi_data.get("paths", {})
    for path in paths_to_check:
        status = "EXISTS" if path in existing_paths else "MISSING"
        print(f"Path {path}: {status}")

    if "/options/execute" not in existing_paths:
        print("/options/execute not found in OpenAPI, cannot proceed with matrix.")
        return

    # 3) Matrix for all 25 strategies
    # List of strategies as inferred from typical requirements or known codebase
    strategies = [
        "bull_call_spread", "bear_put_spread", "iron_condor", "long_straddle",
        "long_strangle", "bull_put_spread", "bear_call_spread", "iron_butterfly",
        "protective_put", "covered_call", "long_call", "long_put",
        "calendar_call_spread", "calendar_put_spread", "diagonal_call_spread",
        "diagonal_put_spread", "butterfly_call_spread", "butterfly_put_spread",
        "ratio_call_spread", "ratio_put_spread", "custom", "cash_secured_put",
        "collar", "synthetic_long", "synthetic_short"
    ]
    
    # We might need to infer bias based on strategy name if the API requires it
    # For now, let's try sending without bias or with a default if it fails
    
    results = []
    
    print("\nRunning strategy matrix...")
    for strategy in strategies:
        payload = {
            "symbol": "SPY",
            "strategy": strategy,
            "quantity": 1,
            "preview": False
        }
        
        try:
            # We don't have auth headers in the request, this might fail if protected
            resp = requests.post(f"{BASE_URL}/options/execute", json=payload)
            data = {}
            try:
                data = resp.json()
            except:
                pass
            
            results.append({
                "strategy": strategy,
                "status": resp.status_code,
                "data": data,
                "headers": dict(resp.headers)
            })
        except Exception as e:
            results.append({
                "strategy": strategy,
                "status": "ERROR",
                "detail": str(e)
            })

    # 4) & 5) Record and Summarize
    print("\nResults Summary:")
    print(f"{'Strategy':<25} | {'Status':<6} | {'Approved':<8} | {'Order ID':<10}")
    print("-" * 60)
    
    summary_status = {}
    summary_outcome = {"approved": 0, "blocked": 0, "submitted": 0, "exception": 0, "unauthorized": 0}
    
    representative_error = None

    for res in results:
        strategy = res["strategy"]
        status = res["status"]
        summary_status[status] = summary_status.get(status, 0) + 1
        
        approved = "N/A"
        order_id = "N/A"
        
        if status == 401 or status == 403:
             summary_outcome["unauthorized"] += 1
             if not representative_error:
                 representative_error = res
        elif status == "ERROR":
            summary_outcome["exception"] += 1
        else:
            data = res.get("data", {})
            approved = data.get("approved", "N/A")
            order_id = data.get("order_response", {}).get("id", "N/A") if isinstance(data.get("order_response"), dict) else "N/A"
            
            if approved is True:
                summary_outcome["approved"] += 1
            elif approved is False:
                summary_outcome["blocked"] += 1
            
            if order_id != "N/A":
                summary_outcome["submitted"] += 1

        print(f"{strategy:<25} | {str(status):<6} | {str(approved):<8} | {str(order_id):<10}")

    print("\n--- Aggregate Report ---")
    print(f"HTTP Status counts: {summary_status}")
    print(f"Outcomes: {summary_outcome}")

    if representative_error:
        print("\n--- Representative Auth/Rate-Limit Error ---")
        print(f"Status: {representative_error['status']}")
        print(f"Headers: {json.dumps(representative_error['headers'], indent=2)}")
        print(f"Body: {json.dumps(representative_error['data'], indent=2)}")

if __name__ == "__main__":
    test_api()
