import requests
import pyotp
import uuid
from collections import Counter

BASE_URL = "https://ghostalphaterminal-production.up.railway.app"
FINGERPRINT = "copilot-matrix-runner"

session = requests.Session()
session.headers.update({"x-device-fingerprint": FINGERPRINT})

def update_csrf():
    csrf = session.cookies.get("ghost_csrf")
    if csrf:
        session.headers.update({"x-csrf-token": csrf})

def full_flow():
    email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    password = "Password123!"
    
    print(f"Initiating 2FA for {email}...")
    try:
        r1 = session.post(f"{BASE_URL}/auth/initiate-2fa", json={"email": email, "twoFAMethod": "totp"}, timeout=15)
        update_csrf()
        if r1.status_code != 200:
            print(f"initiate-2fa failed: {r1.status_code} {r1.text}")
            return
        secret = r1.json()["secret"]
        totp = pyotp.TOTP(secret)
        
        print("Verifying 2FA setup...")
        r2 = session.post(f"{BASE_URL}/auth/verify-2fa-setup", json={"email": email, "twoFAMethod": "totp", "verificationCode": totp.now()}, timeout=15)
        update_csrf()
        if r2.status_code != 200:
            print(f"verify-2fa-setup failed: {r2.status_code} {r2.text}")
            return
            
        print("Completing signup...")
        r3 = session.post(f"{BASE_URL}/auth/signup-complete", json={
            "fullName": "Test User", "email": email, "password": password, 
            "twoFAMethod": "totp", "agreePrivacy": True, "agreeTerms": True, "agreeRisk": True
        }, timeout=15)
        update_csrf()
        if r3.status_code not in [200, 201]:
            print(f"signup-complete failed: {r3.status_code} {r3.text}")
            return

        print("Checking /auth/me...")
        me = session.get(f"{BASE_URL}/auth/me", timeout=15)
        update_csrf()
        if me.status_code != 200:
            print(f"Authentication failed: {me.status_code} {me.text}")
            return

        print("Elevating to high trust...")
        session.post(f"{BASE_URL}/auth/2fa/challenge", json={}, timeout=15)
        update_csrf()
        r_ver = session.post(f"{BASE_URL}/auth/2fa/verify", json={
            "verificationCode": totp.now(),
            "trustDevice": True,
            "deviceLabel": FINGERPRINT
        }, timeout=15)
        update_csrf()
        if r_ver.status_code != 200:
            print(f"Elevation failed: {r_ver.status_code} {r_ver.text}")
            return
            
        ht = session.get(f"{BASE_URL}/auth/session/high-trust-status", timeout=15)
        if not ht.json().get("high_trust_active"):
            print("High trust not active despite verification.")
            return
        
        strategies = [
            "iron_condor", "vertical_spread", "straddle", "strangle", "butterfly",
            "calendar_spread", "diagonal_spread", "iron_butterfly", "covered_call", "protective_put",
            "bull_call_spread", "bear_put_spread", "bull_put_spread", "bear_call_spread", "long_call",
            "long_put", "short_call", "short_put", "ratio_spread", "backspread",
            "condor", "box_spread", "collar", "wheel", "strangle_swap"
        ]
        
        results = []
        print(f"Running {len(strategies)} strategies...")
        for strat in strategies:
            try:
                resp = session.post(f"{BASE_URL}/options/execute", json={
                    "symbol": "SPY",
                    "qty": 1,
                    "strategy_name": strat,
                    "preview": False
                }, timeout=15)
                update_csrf()
                data = resp.json() if resp.status_code == 200 else None
                results.append({
                    "strategy": strat, "status": resp.status_code, "resp_data": data,
                    "error_body": resp.text if resp.status_code != 200 else None
                })
            except Exception as e:
                results.append({"strategy": strat, "status": "TIMEOUT", "error": str(e)})

        print("\n--- Strategy Matrix Results ---")
        header = f"{'Strategy':<20} | {'Status':<7} | {'Approved':<8} | {'Order ID':<10}"
        print(header)
        print("-" * len(header))
        
        counts = Counter()
        status_counts = Counter()
        errors = {}
        
        for r in results:
            status = r["status"]
            status_counts[status] += 1
            strat = r["strategy"]
            if status == 200:
                d = r["resp_data"]
                approved = d.get("approved", False)
                order_id = d.get("order_response", {}).get("id") if d.get("order_response") else "N/A"
                if d.get("order_response"): counts["submitted_with_order_response"] += 1
                elif approved: counts["approved_without_submission"] += 1
                else: counts["blocked"] += 1
                print(f"{strat:<20} | {status:<7} | {str(approved):<8} | {str(order_id):<10}")
            else:
                counts["blocked" if status != "TIMEOUT" else "exceptions"] += 1
                if status != "TIMEOUT" and status not in errors:
                    errors[status] = r["error_body"]
                print(f"{strat:<20} | {status:<7} | {'N/A':<8} | {'N/A':<10}")

        print("\n--- Aggregates ---")
        for k in ["submitted_with_order_response", "approved_without_submission", "blocked", "exceptions"]:
            print(f"{k}: {counts[k]}")
        print("\nBy Status Code:")
        for k, v in sorted(status_counts.items(), key=lambda x: str(x[0])):
            print(f"{k}: {v}")
        if errors:
            print("\n--- Representative Error Bodies ---")
            for code, body in errors.items():
                print(f"Status {code}: {body[:200]}...")
                
    except Exception as e:
        print(f"Flow Exception: {str(e)}")

if __name__ == "__main__":
    full_flow()
