import json
import secrets
import hashlib
import hmac
from datetime import datetime, timedelta, timezone
from typing import Literal
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.models.schemas import (
    AlpacaAccountPnlResponse,
    AlpacaWithdrawalRequest,
    AlpacaWithdrawalResponse,
    AlpacaOrderRequest,
    AlpacaRequestIdEntry,
    AlpacaRequestIdsResponse,
)
from app.api.deps.auth import CurrentUser, HighTrustUser
from app.db.models import AuthAuditLog, BrokerOAuthConnection, TrustedDevice, User, WithdrawalApproval
from app.db.session import get_session
from app.services.alpaca_client import alpaca_client
from app.core.config import settings
from app.services.request_id_store import request_id_store
from app.services.auth_service import auth_service
from app.services.fraud_agent import fraud_agent
from app.services.twofa_service import twofa_service

router = APIRouter(prefix="/alpaca", tags=["alpaca"])

_OAUTH_STATE_TTL_SECONDS = 600
_OAUTH_PROVIDER = "alpaca"
_oauth_states: dict[str, dict] = {}


def _extract_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        candidate = forwarded.split(",", 1)[0].strip()
        if candidate:
            return candidate
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _audit_broker_event(*, request: Request, user_id: str | None, email: str | None, event_type: str, status: str, metadata: dict | None = None) -> None:
    with get_session() as session:
        session.add(
            AuthAuditLog(
                user_id=user_id,
                email=email,
                event_type=event_type,
                status=status,
                method="alpaca_oauth",
                ip_address=_extract_client_ip(request),
                user_agent=request.headers.get("user-agent"),
                metadata_json=json.dumps(metadata or {}),
                created_at=datetime.now(timezone.utc),
            )
        )


def _purge_expired_oauth_states() -> None:
    now = datetime.now(timezone.utc)
    expired = [state for state, payload in _oauth_states.items() if payload["expires_at"] <= now]
    for state in expired:
        _oauth_states.pop(state, None)


def _parse_json_object(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else {}
    except Exception:
        return {}


def _hour_distance(a: int, b: int) -> int:
    diff = abs(a - b)
    return min(diff, 24 - diff)


def _has_recent_withdrawal_step_up(*, user_id: str, request: Request, now: datetime) -> bool:
    window_minutes = max(1, int(settings.webauthn_assertion_window_minutes or settings.withdrawal_step_up_max_age_minutes))
    min_ts = now - timedelta(minutes=window_minutes)
    fingerprint_hash = auth_service._compute_device_fingerprint(request)
    with get_session() as session:
        row = session.execute(
            select(AuthAuditLog)
            .where(AuthAuditLog.user_id == user_id)
            .where(AuthAuditLog.event_type.in_(["2fa_verify", "webauthn_assertion"]))
            .where(AuthAuditLog.status == "success")
            .where(AuthAuditLog.created_at >= min_ts)
            .where(AuthAuditLog.device_fingerprint_hash == fingerprint_hash)
            .order_by(AuthAuditLog.created_at.desc())
        ).scalars().first()
    return row is not None


def _approval_token_hash(token: str) -> str:
    secret = settings.auth_session_secret or "ghost-alpha-withdraw-approval-secret"
    return hmac.new(secret.encode("utf-8"), token.encode("utf-8"), hashlib.sha256).hexdigest()


def _submit_withdrawal_to_broker(*, amount: float, destination: str, memo: str | None) -> dict:
    if settings.alpaca_paper:
        raise HTTPException(status_code=400, detail="Withdrawals are disabled in paper mode")

    body = {
        "transfer_type": "withdraw",
        "relationship_id": destination,
        "amount": str(amount),
    }
    if memo:
        body["description"] = memo
    return alpaca_client.post("/v2/account/transfers", body=body)


def _compute_trust_score(*, user_id: str, request: Request) -> int:
    fingerprint = auth_service._compute_device_fingerprint(request)
    now = datetime.now(timezone.utc)
    with get_session() as session:
        trusted = session.execute(
            select(TrustedDevice)
            .where(TrustedDevice.user_id == user_id)
            .where(TrustedDevice.device_fingerprint_hash == fingerprint)
            .where(TrustedDevice.trusted_until > now)
        ).scalar_one_or_none()

    if trusted is None:
        return 20
    trusted_until = trusted.trusted_until if trusted.trusted_until.tzinfo else trusted.trusted_until.replace(tzinfo=timezone.utc)
    remaining_days = max(0, int((trusted_until - now).total_seconds() // 86400))
    return min(100, 60 + min(40, remaining_days))


def _evaluate_withdrawal_security(*, user_id: str, request: Request, amount: float, destination: str, now: datetime, session_risk_score: int) -> dict:
    with get_session() as session:
        rows = session.execute(
            select(AuthAuditLog)
            .where(AuthAuditLog.user_id == user_id)
            .where(AuthAuditLog.event_type == "broker_withdrawal")
            .where(AuthAuditLog.status.in_(["success", "held", "submitted", "pending"]))
            .order_by(AuthAuditLog.created_at.desc())
            .limit(250)
        ).scalars().all()

    history_amounts: list[float] = []
    history_hours: list[int] = []
    seen_destinations: set[str] = set()
    successful_withdrawals = 0

    for row in rows:
        metadata = _parse_json_object(row.metadata_json)
        status = str(row.status or "").lower()
        if status in {"success", "submitted", "pending"}:
            successful_withdrawals += 1
        row_destination = str(metadata.get("destination") or "").strip()
        if row_destination:
            seen_destinations.add(row_destination)
        try:
            row_amount = float(metadata.get("amount"))
            if row_amount > 0:
                history_amounts.append(row_amount)
        except Exception:
            pass
        created_at = row.created_at if row.created_at.tzinfo else row.created_at.replace(tzinfo=timezone.utc)
        history_hours.append(int(created_at.hour))

    hold_reasons: list[str] = []
    anomaly_reasons: list[str] = []

    is_first_withdrawal = successful_withdrawals == 0
    destination_is_new = destination not in seen_destinations

    hold_minutes = 0
    if is_first_withdrawal:
        hold_minutes = max(hold_minutes, max(0, int(settings.withdrawal_first_cooldown_minutes)))
        hold_reasons.append("first_withdrawal_cooldown")
    if destination_is_new:
        hold_minutes = max(hold_minutes, max(0, int(settings.withdrawal_new_destination_cooldown_minutes)))
        hold_reasons.append("new_destination_cooldown")

    unusual_amount = False
    if history_amounts:
        baseline_avg = sum(history_amounts) / len(history_amounts)
        multiplier = max(1.0, float(settings.withdrawal_anomaly_amount_multiplier))
        absolute_threshold = max(1.0, float(settings.withdrawal_anomaly_amount_absolute))
        unusual_amount = amount >= max(absolute_threshold, baseline_avg * multiplier)
    else:
        unusual_amount = amount >= max(1.0, float(settings.withdrawal_anomaly_amount_absolute))
    if unusual_amount:
        anomaly_reasons.append("unusual_amount")

    unusual_timing = False
    if history_hours:
        mean_hour = int(round(sum(history_hours) / len(history_hours))) % 24
        unusual_timing = _hour_distance(now.hour, mean_hour) >= max(1, int(settings.withdrawal_anomaly_timing_hour_delta))
    if unusual_timing:
        anomaly_reasons.append("unusual_timing")

    if destination_is_new:
        anomaly_reasons.append("unusual_destination")

    trust_score = _compute_trust_score(user_id=user_id, request=request)
    anomaly_score = min(100, 35 * len(anomaly_reasons) + (15 if destination_is_new else 0))
    behavior_score = 0
    if history_amounts:
        baseline = sum(history_amounts) / len(history_amounts)
        if amount >= baseline * 2:
            behavior_score += 40
    if history_hours:
        mean_hour = int(round(sum(history_hours) / len(history_hours))) % 24
        if _hour_distance(now.hour, mean_hour) >= max(1, int(settings.withdrawal_anomaly_timing_hour_delta)):
            behavior_score += 35
    if destination_is_new:
        behavior_score += 25
    behavior_score = min(100, behavior_score)

    fraud = fraud_agent.assess_withdrawal(
        trust_score=trust_score,
        anomaly_score=anomaly_score,
        behavior_score=behavior_score,
        destination_is_new=destination_is_new,
        session_risk_score=session_risk_score,
    )

    risk_rating = fraud.rating
    risk_score = int(fraud.score)

    requires_confirmation = False
    if anomaly_reasons and bool(settings.withdrawal_hold_on_anomaly):
        requires_confirmation = True
        hold_minutes = max(hold_minutes, max(1, int(settings.withdrawal_new_destination_cooldown_minutes)))
        hold_reasons.append("anomaly_hold")

    if fraud.action in {"HOLD", "ESCALATE"}:
        hold_minutes = max(hold_minutes, max(1, int(settings.withdrawal_approval_ttl_minutes)))
        hold_reasons.append("fraud_agent_hold")
        requires_confirmation = True
    if fraud.action == "BLOCK":
        hold_reasons.append("fraud_agent_block")

    hold_until: datetime | None = None
    if hold_minutes > 0:
        hold_until = now + timedelta(minutes=hold_minutes)

    return {
        "risk_score": risk_score,
        "risk_rating": risk_rating,
        "risk_components": {
            "trust_score": trust_score,
            "anomaly_score": anomaly_score,
            "behavior_score": behavior_score,
        },
        "fraud_action": fraud.action,
        "fraud_reasons": fraud.reasons,
        "hold_until": hold_until,
        "hold_reasons": list(dict.fromkeys(hold_reasons)),
        "requires_confirmation": requires_confirmation,
        "anomaly_reasons": anomaly_reasons,
        "destination_is_new": destination_is_new,
        "is_first_withdrawal": is_first_withdrawal,
    }


def _alpaca_oauth_ready() -> bool:
    return bool(
        settings.alpaca_connect_client_id
        and settings.alpaca_connect_client_secret
        and settings.alpaca_connect_redirect_uri
    )


def _save_oauth_tokens(*, payload: dict, user_id: str) -> None:
    now = datetime.now(timezone.utc)
    with get_session() as session:
        connection = session.execute(
            select(BrokerOAuthConnection).where(
                BrokerOAuthConnection.provider == _OAUTH_PROVIDER,
                BrokerOAuthConnection.user_id == user_id,
            )
        ).scalar_one_or_none()
        if connection is None:
            connection = BrokerOAuthConnection(provider=_OAUTH_PROVIDER, user_id=user_id)
            session.add(connection)

        # Stored for broker continuity only; never returned in API responses.
        connection.connected = True
        connection.access_token = payload.get("access_token")
        connection.refresh_token = payload.get("refresh_token")
        connection.token_type = payload.get("token_type")
        connection.scope = payload.get("scope")
        connection.expires_in = payload.get("expires_in")
        connection.obtained_at = now
        connection.disconnected_at = None
        connection.last_error = None
        connection.updated_at = now


def _mark_oauth_error(*, message: str, user_id: str) -> None:
    now = datetime.now(timezone.utc)
    with get_session() as session:
        connection = session.execute(
            select(BrokerOAuthConnection).where(
                BrokerOAuthConnection.provider == _OAUTH_PROVIDER,
                BrokerOAuthConnection.user_id == user_id,
            )
        ).scalar_one_or_none()
        if connection is None:
            connection = BrokerOAuthConnection(provider=_OAUTH_PROVIDER, user_id=user_id)
            session.add(connection)
        connection.last_error = message
        connection.updated_at = now


@router.get("/oauth/status", summary="Get persisted Alpaca OAuth connection status")
def get_oauth_status(user: User = CurrentUser) -> dict:
    with get_session() as session:
        connection = session.execute(
            select(BrokerOAuthConnection).where(
                BrokerOAuthConnection.provider == _OAUTH_PROVIDER,
                BrokerOAuthConnection.user_id == str(user.id),
            )
        ).scalar_one_or_none()

    connected = bool(connection and connection.connected and connection.access_token)
    return {
        "provider": "alpaca",
        "connected": connected,
        "permissions": "Trading (User Authorized)" if connected else "Not Authorized",
        "paper_mode": settings.alpaca_paper,
        "mode": "Paper Trading" if settings.alpaca_paper else "Live Trading",
        "token_type": connection.token_type if connection else None,
        "scope": connection.scope if connection else None,
        "obtained_at": connection.obtained_at.isoformat() if connection and connection.obtained_at else None,
        "expires_in": connection.expires_in if connection else None,
        "updated_at": connection.updated_at.isoformat() if connection and connection.updated_at else None,
        "oauth_ready": _alpaca_oauth_ready(),
    }


@router.post("/oauth/disconnect", summary="Disconnect Alpaca OAuth and clear persisted broker tokens")
def disconnect_oauth(request: Request, user: User = HighTrustUser) -> dict:
    now = datetime.now(timezone.utc)
    with get_session() as session:
        connection = session.execute(
            select(BrokerOAuthConnection).where(
                BrokerOAuthConnection.provider == _OAUTH_PROVIDER,
                BrokerOAuthConnection.user_id == str(user.id),
            )
        ).scalar_one_or_none()
        if connection is None:
            _audit_broker_event(
                request=request,
                user_id=str(user.id),
                email=str(user.email),
                event_type="broker_oauth_disconnect",
                status="success",
                metadata={"provider": _OAUTH_PROVIDER, "connection_existed": False},
            )
            return {
                "provider": "alpaca",
                "disconnected": True,
                "connected": False,
                "updated_at": now.isoformat(),
            }

        connection.connected = False
        connection.access_token = None
        connection.refresh_token = None
        connection.token_type = None
        connection.scope = None
        connection.expires_in = None
        connection.disconnected_at = now
        connection.updated_at = now

    _audit_broker_event(
        request=request,
        user_id=str(user.id),
        email=str(user.email),
        event_type="broker_oauth_disconnect",
        status="success",
        metadata={"provider": _OAUTH_PROVIDER, "connection_existed": True},
    )

    return {
        "provider": "alpaca",
        "disconnected": True,
        "connected": False,
        "updated_at": now.isoformat(),
    }


@router.get(
    "/request-ids",
    response_model=AlpacaRequestIdsResponse,
    summary="Recent Alpaca X-Request-ID values",
    description=(
        "Returns the most recent X-Request-ID header values captured from Alpaca "
        "API responses. Include these IDs when opening a support request with "
        "Alpaca so they can trace the call through their system."
    ),
)
def get_recent_request_ids(
    limit: int = Query(default=50, ge=1, le=100),
) -> AlpacaRequestIdsResponse:
    entries = request_id_store.get_recent(n=limit)
    return AlpacaRequestIdsResponse(
        recent=[
            AlpacaRequestIdEntry(
                alpaca_request_id=e.alpaca_request_id,
                endpoint=e.endpoint,
                method=e.method,
                status_code=e.status_code,
                timestamp=e.timestamp,
                symbol=e.symbol,
            )
            for e in reversed(entries)  # newest first
        ],
        total_captured=request_id_store.total_captured,
    )


def _raise_alpaca_error(err: httpx.HTTPStatusError) -> None:
    """Convert Alpaca HTTP errors to FastAPI HTTPException while preserving context."""
    detail: str
    try:
        payload = err.response.json()
        detail = json.dumps(payload)
    except Exception:
        detail = err.response.text or str(err)
    raise HTTPException(status_code=err.response.status_code, detail=detail)


@router.get("/account", summary="Get Alpaca account information")
def get_account(user: User = HighTrustUser) -> dict:
    try:
        return alpaca_client.get("/v2/account")
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.get("/config-check", summary="Safe Alpaca configuration diagnostics")
def alpaca_config_check() -> dict:
    """Return non-secret configuration status to quickly verify deployment wiring."""
    return {
        "alpaca_api_key_present": bool(settings.alpaca_api_key),
        "alpaca_secret_key_present": bool(settings.alpaca_secret_key),
        "alpaca_paper": settings.alpaca_paper,
        "alpaca_connect_client_id_present": bool(settings.alpaca_connect_client_id),
        "alpaca_connect_client_secret_present": bool(settings.alpaca_connect_client_secret),
        "alpaca_connect_redirect_uri": settings.alpaca_connect_redirect_uri,
        "alpaca_connect_authorize_url": settings.alpaca_connect_authorize_url,
        "alpaca_connect_token_url": settings.alpaca_connect_token_url,
        "alpaca_connect_oauth_ready": _alpaca_oauth_ready(),
        "app_env": settings.app_env,
    }


@router.get("/oauth/start", summary="Start Alpaca Connect OAuth flow")
def start_oauth_flow(
    request: Request,
    next_path: str = Query(default="/alpha", alias="next"),
    user: User = HighTrustUser,
) -> RedirectResponse:
    if not _alpaca_oauth_ready():
        raise HTTPException(
            status_code=500,
            detail=(
                "Alpaca Connect OAuth not configured. Set ALPACA_CONNECT_CLIENT_ID, "
                "ALPACA_CONNECT_CLIENT_SECRET, and ALPACA_CONNECT_REDIRECT_URI."
            ),
        )

    _purge_expired_oauth_states()
    state = secrets.token_urlsafe(24)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=_OAUTH_STATE_TTL_SECONDS)
    _oauth_states[state] = {
        "user_id": str(user.id),
        "next": next_path if next_path.startswith("/") else "/alpha",
        "expires_at": expires_at,
    }

    query = {
        "client_id": settings.alpaca_connect_client_id,
        "redirect_uri": settings.alpaca_connect_redirect_uri,
        "response_type": "code",
        "state": state,
    }
    auth_url = f"{settings.alpaca_connect_authorize_url}?{urlencode(query)}"
    _audit_broker_event(
        request=request,
        user_id=str(user.id),
        email=str(user.email),
        event_type="broker_oauth_start",
        status="success",
        metadata={"provider": _OAUTH_PROVIDER},
    )
    return RedirectResponse(url=auth_url, status_code=307)


@router.get("/oauth/callback", summary="Exchange Alpaca OAuth code for tokens")
def complete_oauth_flow(
    request: Request,
    code: str = Query(..., min_length=1),
    state: str = Query(..., min_length=1),
) -> RedirectResponse:
    if not _alpaca_oauth_ready():
        raise HTTPException(status_code=500, detail="Alpaca Connect OAuth is not configured")

    _purge_expired_oauth_states()
    state_payload = _oauth_states.pop(state, None)
    if state_payload is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")

    token_body = {
        "grant_type": "authorization_code",
        "code": code,
        "client_id": settings.alpaca_connect_client_id,
        "client_secret": settings.alpaca_connect_client_secret,
        "redirect_uri": settings.alpaca_connect_redirect_uri,
    }

    try:
        with httpx.Client(timeout=15) as client:
            resp = client.post(
                settings.alpaca_connect_token_url,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                data=token_body,
            )
        resp.raise_for_status()
        payload = resp.json()
    except httpx.HTTPStatusError as err:
        state_user_id = str(state_payload.get("user_id", "") or "")
        if state_user_id:
            _mark_oauth_error(message=str(err.response.text or err), user_id=state_user_id)
        _raise_alpaca_error(err)
    except Exception as err:
        state_user_id = str(state_payload.get("user_id", "") or "")
        if state_user_id:
            _mark_oauth_error(message=str(err), user_id=state_user_id)
        raise HTTPException(status_code=502, detail=f"OAuth token exchange failed: {err}")

    state_user_id = str(state_payload.get("user_id", "") or "")
    if not state_user_id:
        raise HTTPException(status_code=400, detail="OAuth state missing user identity")

    _save_oauth_tokens(payload=payload, user_id=state_user_id)
    _audit_broker_event(
        request=request,
        user_id=state_user_id,
        email=None,
        event_type="broker_oauth_complete",
        status="success",
        metadata={"provider": _OAUTH_PROVIDER},
    )

    next_path = str(state_payload.get("next", "/alpha") or "/alpha")
    if not next_path.startswith("/"):
        next_path = "/alpha"
    redirect_to = f"{settings.frontend_base_url.rstrip('/')}{next_path}?alpaca_oauth=connected"
    return RedirectResponse(url=redirect_to, status_code=307)


@router.get(
    "/account/pnl",
    response_model=AlpacaAccountPnlResponse,
    summary="Get account day gain/loss from equity vs last equity",
)
def get_account_pnl(user: User = HighTrustUser) -> AlpacaAccountPnlResponse:
    try:
        account = alpaca_client.get("/v2/account")
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)

    equity = float(account.get("equity", 0.0))
    last_equity = float(account.get("last_equity", 0.0))
    return AlpacaAccountPnlResponse(
        equity=equity,
        last_equity=last_equity,
        balance_change=round(equity - last_equity, 6),
    )


@router.get("/assets", summary="List assets from Alpaca")
def list_assets(
    status: Literal["active", "inactive"] = Query(default="active"),
    asset_class: Literal["us_equity", "crypto"] = Query(default="us_equity"),
    user: User = HighTrustUser,
) -> list[dict]:
    try:
        result = alpaca_client.get(
            "/v2/assets",
            params={"status": status, "asset_class": asset_class},
        )
        if isinstance(result, list):
            return result
        return [result]
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.get("/assets/{symbol}", summary="Get one asset by symbol")
def get_asset(symbol: str, user: User = HighTrustUser) -> dict:
    try:
        return alpaca_client.get(f"/v2/assets/{symbol.upper()}", symbol=symbol.upper())
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.post("/orders", summary="Submit a new order to Alpaca")
def submit_order(payload: AlpacaOrderRequest, user: User = HighTrustUser) -> dict:
    body = payload.model_dump(exclude_none=True)
    # qty or notional is required by Alpaca for order creation
    if "qty" not in body and "notional" not in body:
        raise HTTPException(status_code=422, detail="Either qty or notional must be provided")
    try:
        return alpaca_client.post("/v2/orders", body=body, symbol=payload.symbol.upper())
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.post("/withdrawals", response_model=AlpacaWithdrawalResponse, summary="Request a cash withdrawal")
def request_withdrawal(payload: AlpacaWithdrawalRequest, request: Request, user: User = HighTrustUser) -> AlpacaWithdrawalResponse:
    now = datetime.now(timezone.utc)
    user_id = str(user.id)
    user_email = str(user.email)

    if not _has_recent_withdrawal_step_up(user_id=user_id, request=request, now=now):
        _audit_broker_event(
            request=request,
            user_id=user_id,
            email=user_email,
            event_type="broker_withdrawal",
            status="rejected",
            metadata={
                "provider": _OAUTH_PROVIDER,
                "amount": payload.amount,
                "destination": payload.destination,
                "reason": "missing_recent_step_up",
            },
        )
        raise HTTPException(status_code=403, detail="Withdrawal step-up required (OTP or passkey)")

    context = auth_service.get_current_context(request)
    session_risk_reasons: list[str] = []
    try:
        session_risk_reasons = json.loads(str(context.session.risk_reasons_json or "[]"))
    except Exception:
        session_risk_reasons = []

    security = _evaluate_withdrawal_security(
        user_id=user_id,
        request=request,
        amount=float(payload.amount),
        destination=str(payload.destination),
        now=now,
        session_risk_score=int(context.session.risk_score or 0),
    )

    # Always notify user on initiation attempt for transparency.
    twofa_service.send_security_alert(
        to_email=user_email,
        method="withdrawal",
        ip_address=_extract_client_ip(request),
        device=request.headers.get("user-agent"),
        location=request.headers.get("x-geo-country") or request.headers.get("x-geo-city"),
        event="Withdrawal initiated",
    )

    if "new_device" in session_risk_reasons:
        twofa_service.send_security_alert(
            to_email=user_email,
            method="withdrawal",
            ip_address=_extract_client_ip(request),
            device=request.headers.get("user-agent"),
            location=request.headers.get("x-geo-country") or request.headers.get("x-geo-city"),
            event="New device withdrawal attempt",
        )

    if security["destination_is_new"]:
        twofa_service.send_security_alert(
            to_email=user_email,
            method="withdrawal",
            ip_address=_extract_client_ip(request),
            device=request.headers.get("user-agent"),
            location=request.headers.get("x-geo-country") or request.headers.get("x-geo-city"),
            event="Withdrawal to new destination",
        )

    if security["fraud_action"] == "BLOCK":
        twofa_service.send_security_alert(
            to_email=user_email,
            method="withdrawal",
            ip_address=_extract_client_ip(request),
            device=request.headers.get("user-agent"),
            location=request.headers.get("x-geo-country") or request.headers.get("x-geo-city"),
            event="Withdrawal blocked by fraud agent",
        )
        _audit_broker_event(
            request=request,
            user_id=user_id,
            email=user_email,
            event_type="broker_withdrawal",
            status="blocked",
            metadata={
                "provider": _OAUTH_PROVIDER,
                "amount": payload.amount,
                "destination": payload.destination,
                "risk_score": security["risk_score"],
                "risk_rating": security["risk_rating"],
                "fraud_reasons": security["fraud_reasons"],
            },
        )
        raise HTTPException(status_code=403, detail="Withdrawal blocked for fraud review")

    if security["hold_until"] is not None:
        confirm_token = secrets.token_urlsafe(32)
        deny_token = secrets.token_urlsafe(32)
        approval_id: int | None = None
        with get_session() as session:
            approval = WithdrawalApproval(
                user_id=user_id,
                amount=float(payload.amount),
                destination=str(payload.destination),
                memo=payload.memo,
                request_metadata_json=json.dumps(
                    {
                        "hold_reasons": security["hold_reasons"],
                        "risk_score": security["risk_score"],
                        "risk_rating": security["risk_rating"],
                        "risk_components": security["risk_components"],
                        "fraud_action": security["fraud_action"],
                        "fraud_reasons": security["fraud_reasons"],
                    }
                ),
                confirm_token_hash=_approval_token_hash(confirm_token),
                deny_token_hash=_approval_token_hash(deny_token),
                status="PENDING",
                expires_at=security["hold_until"],
                created_at=now,
            )
            session.add(approval)
            session.flush()
            approval_id = int(approval.id)

        confirm_link = f"{settings.frontend_base_url.rstrip('/')}/api/withdrawals/approve?token={confirm_token}"
        deny_link = f"{settings.frontend_base_url.rstrip('/')}/api/withdrawals/deny?token={deny_token}"
        hold_minutes = max(1, int((security["hold_until"] - now).total_seconds() // 60))
        try:
            twofa_service.send_withdrawal_approval_email(
                to_email=user_email,
                amount=float(payload.amount),
                destination=str(payload.destination),
                confirm_link=confirm_link,
                deny_link=deny_link,
                hold_minutes=hold_minutes,
            )
        except Exception:
            pass

        _audit_broker_event(
            request=request,
            user_id=user_id,
            email=user_email,
            event_type="broker_withdrawal",
            status="held",
            metadata={
                "provider": _OAUTH_PROVIDER,
                "amount": payload.amount,
                "destination": payload.destination,
                "approval_id": approval_id,
                "hold_until": security["hold_until"].isoformat(),
                "hold_reasons": security["hold_reasons"],
                "requires_confirmation": security["requires_confirmation"],
                "anomaly_reasons": security["anomaly_reasons"],
                "risk_score": security["risk_score"],
                "risk_rating": security["risk_rating"],
                "risk_components": security["risk_components"],
                "fraud_action": security["fraud_action"],
                "fraud_reasons": security["fraud_reasons"],
            },
        )
        return AlpacaWithdrawalResponse(
            status="PENDING",
            transfer_id=None,
            amount=payload.amount,
            destination=payload.destination,
            requested_at=now,
            hold_until=security["hold_until"],
            hold_reasons=security["hold_reasons"],
            requires_confirmation=bool(security["requires_confirmation"]),
            risk_score=int(security["risk_score"]),
            risk_rating=str(security["risk_rating"]),
            risk_components=security["risk_components"],
            approval_id=approval_id,
        )

    try:
        transfer = _submit_withdrawal_to_broker(
            amount=float(payload.amount),
            destination=str(payload.destination),
            memo=payload.memo,
        )
    except httpx.HTTPStatusError as err:
        _audit_broker_event(
            request=request,
            user_id=user_id,
            email=user_email,
            event_type="broker_withdrawal",
            status="failed",
            metadata={
                "provider": _OAUTH_PROVIDER,
                "amount": payload.amount,
                "destination": payload.destination,
                "error": str(err),
                "risk_score": security["risk_score"],
                "risk_rating": security["risk_rating"],
            },
        )
        _raise_alpaca_error(err)
    except HTTPException as err:
        _audit_broker_event(
            request=request,
            user_id=user_id,
            email=user_email,
            event_type="broker_withdrawal",
            status="rejected",
            metadata={
                "provider": _OAUTH_PROVIDER,
                "amount": payload.amount,
                "destination": payload.destination,
                "reason": str(err.detail),
                "risk_score": security["risk_score"],
                "risk_rating": security["risk_rating"],
            },
        )
        raise

    transfer_id = str(transfer.get("id") or transfer.get("transfer_id") or "") or None
    _audit_broker_event(
        request=request,
        user_id=user_id,
        email=user_email,
        event_type="broker_withdrawal",
        status="success",
        metadata={
            "provider": _OAUTH_PROVIDER,
            "amount": payload.amount,
            "destination": payload.destination,
            "transfer_id": transfer_id,
            "risk_score": security["risk_score"],
            "risk_rating": security["risk_rating"],
            "risk_components": security["risk_components"],
        },
    )

    return AlpacaWithdrawalResponse(
        status="SUBMITTED",
        transfer_id=transfer_id,
        amount=payload.amount,
        destination=payload.destination,
        requested_at=now,
        risk_score=int(security["risk_score"]),
        risk_rating=str(security["risk_rating"]),
        risk_components=security["risk_components"],
    )


@router.get("/withdrawals/approval/confirm", summary="One-click confirm a held withdrawal")
def confirm_withdrawal_approval(request: Request, token: str = Query(..., min_length=16)) -> dict:
    now = datetime.now(timezone.utc)
    token_hash = _approval_token_hash(token)
    with get_session() as session:
        row = session.execute(
            select(WithdrawalApproval)
            .where(WithdrawalApproval.confirm_token_hash == token_hash)
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Approval token not found")
        if row.status != "PENDING":
            return {"success": True, "status": row.status}
        if (row.expires_at if row.expires_at.tzinfo else row.expires_at.replace(tzinfo=timezone.utc)) <= now:
            row.status = "EXPIRED"
            row.resolved_at = now
            raise HTTPException(status_code=410, detail="Approval token expired")

        try:
            transfer = _submit_withdrawal_to_broker(amount=float(row.amount), destination=str(row.destination), memo=row.memo)
            transfer_id = str(transfer.get("id") or transfer.get("transfer_id") or "") or None
            row.status = "APPROVED"
            row.resolved_at = now
            _audit_broker_event(
                request=request,
                user_id=row.user_id,
                email=None,
                event_type="broker_withdrawal_approval",
                status="approved",
                metadata={"approval_id": row.id, "transfer_id": transfer_id},
            )
            return {"success": True, "status": "APPROVED", "transfer_id": transfer_id}
        except HTTPException as err:
            row.status = "REJECTED"
            row.resolved_at = now
            _audit_broker_event(
                request=request,
                user_id=row.user_id,
                email=None,
                event_type="broker_withdrawal_approval",
                status="rejected",
                metadata={"approval_id": row.id, "reason": str(err.detail)},
            )
            raise err
        except httpx.HTTPStatusError as err:
            row.status = "REJECTED"
            row.resolved_at = now
            _audit_broker_event(
                request=request,
                user_id=row.user_id,
                email=None,
                event_type="broker_withdrawal_approval",
                status="failed",
                metadata={"approval_id": row.id, "error": str(err)},
            )
            _raise_alpaca_error(err)


@router.get("/withdrawals/approval/deny", summary="One-click deny a held withdrawal")
def deny_withdrawal_approval(request: Request, token: str = Query(..., min_length=16)) -> dict:
    now = datetime.now(timezone.utc)
    token_hash = _approval_token_hash(token)
    with get_session() as session:
        row = session.execute(
            select(WithdrawalApproval)
            .where(WithdrawalApproval.deny_token_hash == token_hash)
        ).scalar_one_or_none()
        if row is None:
            raise HTTPException(status_code=404, detail="Approval token not found")
        if row.status != "PENDING":
            return {"success": True, "status": row.status}
        row.status = "DENIED"
        row.resolved_at = now
        _audit_broker_event(
            request=request,
            user_id=row.user_id,
            email=None,
            event_type="broker_withdrawal_approval",
            status="denied",
            metadata={"approval_id": row.id},
        )
    return {"success": True, "status": "DENIED"}


@router.get("/orders", summary="List Alpaca orders")
def list_orders(
    status: str = Query(default="open"),
    limit: int = Query(default=50, ge=1, le=500),
    nested: bool = Query(default=True),
    user: User = HighTrustUser,
) -> list[dict]:
    try:
        result = alpaca_client.get(
            "/v2/orders",
            params={"status": status, "limit": limit, "nested": str(nested).lower()},
        )
        if isinstance(result, list):
            return result
        return [result]
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.get("/orders/by-client-id/{client_order_id}", summary="Get order by client_order_id")
def get_order_by_client_id(client_order_id: str, user: User = HighTrustUser) -> dict:
    try:
        return alpaca_client.get(
            "/v2/orders:by_client_order_id",
            params={"client_order_id": client_order_id},
        )
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.get("/positions", summary="List all open positions")
def list_positions(user: User = HighTrustUser) -> list[dict]:
    try:
        result = alpaca_client.get("/v2/positions")
        if isinstance(result, list):
            return result
        return [result]
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)


@router.get("/positions/{symbol}", summary="Get a position by symbol")
def get_position(symbol: str, user: User = HighTrustUser) -> dict:
    try:
        return alpaca_client.get(f"/v2/positions/{symbol.upper()}", symbol=symbol.upper())
    except httpx.HTTPStatusError as err:
        _raise_alpaca_error(err)
