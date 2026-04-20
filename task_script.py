import requests
import pyotp
import uuid
import json

BASE_URL = "https://ghostalphaterminal-production.up.railway.app"
EMAIL = f"task_{uuid.uuid4().hex[:6]}@example.com"
PASSWORD = "Password123!"

s = requests.Session()
s.get(f"{BASE_URL}/health")
token = s.cookies.get("ghost_csrf")

def post(p, d):
    return s.post(f"{BASE_URL}{p}", json=d, headers={"x-csrf-token": token if token else ""}, timeout=30)

try:
    sec = post("/auth/initiate-2fa", {"email": EMAIL, "twoFAMethod": "totp"}).json().get("secret")
    t = pyotp.TOTP(sec)
    post("/auth/verify-2fa-setup", {"email": EMAIL, "twoFAMethod": "totp", "verificationCode": t.now()})
    post("/auth/signup-complete", {"email": EMAIL, "password": PASSWORD, "fullName": "T R", "username": f"u{uuid.uuid4().hex[:4]}", "twoFAMethod": "totp", "agreePrivacy": True, "agreeTerms": True, "agreeRisk": True})
    post("/auth/2fa/challenge", {})
    post("/auth/2fa/verify", {"verificationCode": t.now(), "trustDevice": True, "deviceLabel": "r"})
    
    r = post("/options/execute", {"symbol":"SPY","strategy":"LONG_CALL","bias":"BULLISH","quantity":1,"preview":False})
    print(f"Status: {r.status_code}\nBody: {r.text}\nHeaders: { {h: r.headers.get(h) for h in ['X-Request-ID', 'X-API-Scope', 'Retry-After', 'X-RateLimit-Limit', 'X-RateLimit-Window']} }")
    
    rs = s.get(f"{BASE_URL}/options/strategies/supported", timeout=30)
    print(f"\nStrategies Status: {rs.status_code}\nFirst 5: {rs.json()[:5]}")
except Exception as e:
    print(f"Error: {e}")
