import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import pyotp
import uuid
import time
import json

BASE_URL = "https://ghostalphaterminal-production.up.railway.app"
EMAIL = f"matrix_test_{uuid.uuid4().hex[:8]}@example.com"
PASSWORD = "StrongPassword123!"

session = requests.Session()
retries = Retry(total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
session.mount("https://", HTTPAdapter(max_retries=retries))

def get_csrf():
    resp = session.get(f"{BASE_URL}/health")
    return resp.cookies.get("ghost_csrf")

def post(path, data):
    csrf = session.cookies.get("ghost_csrf")
    headers = {"x-csrf-token": csrf} if csrf else {}
    return session.post(f"{BASE_URL}{path}", json=data, headers=headers, timeout=45)

def get(path):
    return session.get(f"{BASE_URL}{path}", timeout=45)

def run():
    print(f"Starting registration for {EMAIL}...")
    get_csrf()
    
    r1 = post("/auth/initiate-2fa", {"email": EMAIL, "twoFAMethod": "totp"})
    secret = r1.json().get("secret")
    totp = pyotp.TOTP(secret)
    
    post("/auth/verify-2fa-setup", {"email": EMAIL, "twoFAMethod": "totp", "verificationCode": totp.now()})
    
    post("/auth/signup-complete", {
        "email": EMAIL, "password": PASSWORD, "fullName": "Matrix Runner",
        "username": f"user_{uuid.uuid4().hex[:6]}", "twoFAMethod": "totp",
        "agreePrivacy": True, "agreeTerms": True, "agreeRisk": True
    })
    
    post("/auth/2fa/challenge", {})
    post("/auth/2fa/verify", {"verificationCode": totp.now(), "trustDevice": True, "deviceLabel": "runner"})
    
    status = get("/auth/session/high-trust-status").json()
    print(f"High Trust Status: {status}")

    strategies = [
        "LONG_CALL",
        "LONG_PUT",
        "VERTICAL_CALL",
        "VERTICAL_PUT",
        "CALENDAR_CALL",
        "CALENDAR_PUT",
        "DIAGONAL_CALL",
        "DIAGONAL_PUT",
        "RATIO_CALL",
        "RATIO_PUT",
        "BUTTERFLY_CALL",
        "BUTTERFLY_PUT",
        "CONDOR_CALL",
        "CONDOR_PUT",
        "IRON_CONDOR",
        "STRADDLE",
        "STRANGLE",
        "COVERED_CALL",
        "COVERED_PUT",
        "PROTECTIVE_CALL",
        "PROTECTIVE_PUT",
        "CUSTOM_2_LEG",
        "CUSTOM_3_LEG",
        "CUSTOM_4_LEG",
        "CUSTOM_STOCK_OPTION",
    ]

    results = []
    print(f"Executing matrix for {len(strategies)} strategies...")
    for strat in strategies:
        try:
            bias = "NEUTRAL"
            if strat in {"LONG_CALL", "VERTICAL_CALL", "CALENDAR_CALL", "DIAGONAL_CALL", "RATIO_CALL", "COVERED_CALL", "PROTECTIVE_CALL"}:
                bias = "BULLISH"
            elif strat in {"LONG_PUT", "VERTICAL_PUT", "CALENDAR_PUT", "DIAGONAL_PUT", "RATIO_PUT", "COVERED_PUT", "PROTECTIVE_PUT"}:
                bias = "BEARISH"

            payload = {
                "symbol": "SPY",
                "strategy": strat,
                "preview": False,
                "bias": bias,
                "quantity": 1,
            }
            r = post("/options/execute", payload)
            data = r.json() if r.status_code == 200 else {"detail": r.text}
            results.append({
                "strategy": strat,
                "status": r.status_code,
                "request_id": r.headers.get("X-Request-ID"),
                "approved": data.get("approved"),
                "order_response_present": bool(data.get("order_response")),
                "reason": data.get("reason") or data.get("detail"),
            })
            print(".", end="", flush=True)
        except Exception as e:
            results.append({"strategy": strat, "status": "Error", "request_id": None, "reason": str(e)})
            print("x", end="", flush=True)
    print("\nDone.")

    print("\n--- FIRST 10 ROWS ---")
    for res in results[:10]: print(res)
    
    print("\n--- NON-200 ROWS ---")
    for res in results:
        if res.get("status") != 200: print(res)

    status_counts = {}
    submitted_with_order = 0
    approved_no_submit = 0
    blocked = 0
    
    for res in results:
        s = res.get("status")
        status_counts[s] = status_counts.get(s, 0) + 1
        if res.get("order_response_present"): submitted_with_order += 1
        if res.get("approved") and not res.get("order_response_present"): approved_no_submit += 1
        if res.get("approved") == False: blocked += 1

    print("\n--- AGGREGATES ---")
    print(f"Status Codes: {status_counts}")
    print(f"Submitted: {submitted_with_order}")
    print(f"Approved w/o Submit: {approved_no_submit}")
    print(f"Blocked: {blocked}")

run()
