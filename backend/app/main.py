import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.api.routes.agents import router as agents_router
from app.api.routes.alpaca import router as alpaca_router
from app.api.routes.auth import router as auth_router
from app.api.routes.brokers import router as brokers_router
from app.api.routes.orchestrator import router as orchestrator_router
from app.api.routes.backtest import router as backtest_router
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
from app.core.config import settings
from app.db.init_db import initialize_database
from app.services.news.coinbase_ws_service import coinbase_ws_service

app = FastAPI(title=settings.app_name, version=settings.app_version)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Stamp every API response with a unique X-Request-ID header."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = uuid.uuid4().hex  # 32-char hex, matches Alpaca's format
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIdMiddleware)

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
app.include_router(alpaca_router)
app.include_router(agents_router)
app.include_router(orchestrator_router)
app.include_router(metrics_router)
app.include_router(auth_router)
app.include_router(brokers_router)


@app.on_event("startup")
def on_startup() -> None:
    initialize_database()
    coinbase_ws_service.start()


@app.on_event("shutdown")
def on_shutdown() -> None:
    coinbase_ws_service.stop()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
