import uuid
import time
import hmac
import secrets
from urllib.parse import urlparse
from collections import defaultdict, deque
from threading import Lock

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from app.api.routes.agents import router as agents_router
from app.api.routes.alpaca import router as alpaca_router
from app.api.routes.auth import router as auth_router
from app.api.routes.brokers import router as brokers_router
from app.api.routes.orchestrator import router as orchestrator_router
from app.api.routes.backtest import router as backtest_router
from app.api.routes.copilot_agent import router as copilot_agent_router
from app.api.routes.control import router as control_router
from app.api.routes.execute import router as execute_router
from app.api.routes.forecast import router as forecast_router
from app.api.routes.options import router as options_router
from app.api.routes.performance import router as performance_router
from app.api.routes.portfolio import router as portfolio_router
from app.api.routes.signals import router as signals_router
from app.api.routes.swarm import router as swarm_router
from app.api.routes.trade import router as trade_router
from app.api.routes.metrics import router as metrics_router
from app.api.routes.telemetry import router as telemetry_router
from app.api.routes.tradier import router as tradier_router
from app.api.routes.universe import router as universe_router
from app.api.routes.schwab import router as schwab_router
from app.core.config import settings
from app.db.init_db import initialize_database
from app.services.news.coinbase_ws_service import coinbase_ws_service
from app.services.tradier_order_sync_service import tradier_order_sync_service

app = FastAPI(title=settings.app_name, version=settings.app_version)


class CsrfProtectionMiddleware(BaseHTTPMiddleware):
    """Double-submit CSRF protection for cookie-authenticated state-changing requests."""

    _SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}
    _CSRF_COOKIE = "ghost_csrf"

    @staticmethod
    def _has_session_cookie(request: Request) -> bool:
        return bool(request.cookies.get("ghost_auth_session") or request.cookies.get("ghost_auth_access"))

    @staticmethod
    def _same_origin_request(request: Request) -> bool:
        expected = str(settings.frontend_base_url or "").strip()
        if not expected:
            return False
        expected_origin = urlparse(expected)
        if not expected_origin.scheme or not expected_origin.netloc:
            return False

        origin = str(request.headers.get("origin") or "").strip()
        if origin:
            parsed_origin = urlparse(origin)
            return (
                parsed_origin.scheme == expected_origin.scheme
                and parsed_origin.netloc == expected_origin.netloc
            )

        referer = str(request.headers.get("referer") or "").strip()
        if referer:
            parsed_ref = urlparse(referer)
            return (
                parsed_ref.scheme == expected_origin.scheme
                and parsed_ref.netloc == expected_origin.netloc
            )

        return False

    async def dispatch(self, request: Request, call_next) -> Response:
        method = request.method.upper()
        if method not in self._SAFE_METHODS and self._has_session_cookie(request):
            csrf_cookie = str(request.cookies.get(self._CSRF_COOKIE) or "")
            csrf_header = str(request.headers.get("x-csrf-token") or "")
            csrf_valid = bool(csrf_cookie and csrf_header and hmac.compare_digest(csrf_cookie, csrf_header))
            if not csrf_valid and not self._same_origin_request(request):
                response = JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed."},
                )
                response.headers["X-Request-ID"] = uuid.uuid4().hex
                return response

        response = await call_next(request)

        if not request.cookies.get(self._CSRF_COOKIE):
            response.set_cookie(
                key=self._CSRF_COOKIE,
                value=secrets.token_urlsafe(32),
                httponly=False,
                secure=bool(settings.auth_cookie_secure),
                samesite="lax",
                path="/",
            )

        return response


class ApiGuardMiddleware(BaseHTTPMiddleware):
    """Apply lightweight API key scope checks and per-IP rate limiting."""

    _SENSITIVE_PREFIXES = (
        "/execute",
        "/trade",
        "/control",
        "/copilot",
        "/auth",
    )

    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            candidate = forwarded.split(",", 1)[0].strip()
            if candidate:
                return candidate
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    @staticmethod
    def _has_session_cookie(request: Request) -> bool:
        return bool(request.cookies.get("ghost_auth_session") or request.cookies.get("ghost_auth_access"))

    def _resolve_scope(self, request: Request) -> str:
        key = str(request.headers.get("x-api-key") or "").strip()
        if not key:
            return "session" if self._has_session_cookie(request) else "anon"

        if settings.api_key_trading and key == settings.api_key_trading:
            return "trading_key"
        if settings.api_key_readonly and key == settings.api_key_readonly:
            return "readonly_key"
        return "invalid_key"

    @staticmethod
    def _scope_allowed(*, scope: str, path: str, method: str) -> bool:
        if scope != "readonly_key":
            return True
        if method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            return False
        return not path.startswith(ApiGuardMiddleware._SENSITIVE_PREFIXES)

    @staticmethod
    def _scope_limit(scope: str) -> int:
        if scope == "trading_key":
            return max(30, int(settings.api_rate_limit_trading_key or 240))
        if scope == "readonly_key":
            return max(30, int(settings.api_rate_limit_readonly_key or 360))
        if scope == "session":
            return max(30, int(settings.api_rate_limit_session or 240))
        return max(10, int(settings.api_rate_limit_anon or 90))

    def _consume(self, *, bucket: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        with self._lock:
            q = self._hits[bucket]
            cutoff = now - window_seconds
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= limit:
                retry_after = max(1, int(window_seconds - (now - q[0]))) if q else window_seconds
                return False, retry_after
            q.append(now)
            return True, 0

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path == "/health":
            return await call_next(request)

        scope = self._resolve_scope(request)
        if scope == "invalid_key":
            response = JSONResponse(
                status_code=401,
                content={"detail": "Invalid API key."},
            )
            response.headers["X-API-Scope"] = "invalid"
            response.headers["X-Request-ID"] = uuid.uuid4().hex
            return response

        if not self._scope_allowed(scope=scope, path=path, method=request.method):
            response = JSONResponse(
                status_code=403,
                content={"detail": "API key scope does not permit this route or method."},
            )
            response.headers["X-API-Scope"] = scope
            response.headers["X-Request-ID"] = uuid.uuid4().hex
            return response

        limit = self._scope_limit(scope)
        window_seconds = max(10, int(settings.api_rate_limit_window_seconds or 60))
        bucket = f"{scope}:{self._client_ip(request)}"
        allowed, retry_after = self._consume(bucket=bucket, limit=limit, window_seconds=window_seconds)
        if not allowed:
            response = JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded."},
            )
            response.headers["Retry-After"] = str(retry_after)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Window"] = str(window_seconds)
            response.headers["X-API-Scope"] = scope
            response.headers["X-Request-ID"] = uuid.uuid4().hex
            return response

        request.state.api_scope = scope
        response = await call_next(request)
        response.headers["X-API-Scope"] = scope
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Window"] = str(window_seconds)
        return response


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Stamp every API response with a unique X-Request-ID header."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid.uuid4().hex  # 32-char hex, matches Alpaca's format
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if bool(settings.auth_cookie_secure):
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains; preload"
        response.headers["X-Platform-Notice"] = "Ghost Alpha Terminal is software tooling, not investment advice."
        response.headers["X-API-Usage"] = "No reverse engineering, model extraction, or unauthorized signal resale."
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
        return response


app.add_middleware(RequestIdMiddleware)
app.add_middleware(ApiGuardMiddleware)
app.add_middleware(CsrfProtectionMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=settings.cors_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(forecast_router)
app.include_router(options_router)
app.include_router(signals_router)
app.include_router(swarm_router)
app.include_router(trade_router)
app.include_router(performance_router)
app.include_router(backtest_router)
app.include_router(execute_router)
app.include_router(portfolio_router)
app.include_router(control_router)
app.include_router(copilot_agent_router)
app.include_router(alpaca_router)
app.include_router(tradier_router)
app.include_router(agents_router)
app.include_router(orchestrator_router)
app.include_router(metrics_router)
app.include_router(auth_router)
app.include_router(brokers_router)
app.include_router(telemetry_router)
app.include_router(universe_router)
app.include_router(schwab_router)


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()
    coinbase_ws_service.start()
    tradier_order_sync_service.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    coinbase_ws_service.stop()
    tradier_order_sync_service.stop()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
