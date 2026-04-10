"""
/agents  — Agent Swarm Layer API routes

GET  /agents/status           → current agent health + latest decision
GET  /agents/decisions        → recent decision log (newest first)
POST /agents/run-cycle        → execute one full swarm cycle

WebSocket future hook:
  /ws/agents/live  (prepared below — not yet active)
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select

from app.models.schemas import (
    AgentAttribution,
    AllocationDecision,
    AgentWeightHistoryResponse,
    AgentWeightSnapshot,
    AgentWeightEntry,
    BrokerConnectionsResponse,
    AgentWeightsResponse,
    BrokerConnectionEntryResponse,
    BrokerCapabilitiesResponse,
    CapitalSplitRecommendation,
    ContextSignalResponse,
    DecisionAuditDetailResponse,
    DecisionAuditSummaryListResponse,
    DecisionAuditSummaryResponse,
    DecisionReplayResponse,
    DecisionReplayStepResponse,
    DecisionOutcome,
    DecisionOutcomeUpdateRequest,
    ExecutionHistoryEntry,
    ExecutionHistoryResponse,
    ExecutionModeResponse,
    ExecutionModeUpdateRequest,
    GoalStatusResponse,
    GoalTargetRequest,
    NewsAuditEntryResponse,
    NewsAuditResponse,
    NewsSignalResponse,
    NewsSourceWhitelistResponse,
    OpportunitiesResponse,
    OpportunityRecommendation,
    SwarmAgentSignal,
    SwarmCycleRequest,
    SwarmCycleResponse,
    SwarmDecisionListResponse,
    SwarmStatusResponse,
)
from app.core.config import settings
from app.api.deps.auth import CurrentUser
from app.db.models import BrokerOAuthConnection, User
from app.db.session import get_session
from app.services.control_engine import control_engine
from app.services.context_intelligence import context_intelligence
from app.services.decision_audit_store import decision_audit_store
from app.services.swarm.decision_store import swarm_decision_store
from app.services.execution_journal import execution_journal
from app.services.goal_engine import goal_engine
from app.services.news.coinbase_ws_service import coinbase_ws_service
from app.services.news.news_intelligence import news_intelligence
from app.services.opportunity_scanner import opportunity_scanner
from app.services.portfolio_manager import portfolio_manager
from app.services.swarm.execution_bridge import execution_bridge
from app.services.swarm.swarm_manager import swarm_manager
from app.services.swarm.weight_engine import dynamic_weight_engine

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get(
    "/status",
    response_model=SwarmStatusResponse,
    summary="Agent swarm health and latest decision",
)
def get_agent_status() -> SwarmStatusResponse:
    raw = swarm_manager.status()
    return SwarmStatusResponse(
        agents=raw["agents"],
        total_cycles=raw["total_cycles"],
        execution_mode=raw["execution_mode"],
        current_weights=raw.get("current_weights"),
        latest_decision=raw["latest_decision"],
    )


@router.get(
    "/execution-mode",
    response_model=ExecutionModeResponse,
    summary="Get current swarm execution mode",
)
def get_execution_mode() -> ExecutionModeResponse:
    return ExecutionModeResponse(mode=execution_bridge.get_mode())


@router.post(
    "/execution-mode",
    response_model=ExecutionModeResponse,
    summary="Set swarm execution mode",
)
def update_execution_mode(payload: ExecutionModeUpdateRequest) -> ExecutionModeResponse:
    mode = execution_bridge.set_mode(payload.mode)
    return ExecutionModeResponse(mode=mode)


@router.get(
    "/brokers/capabilities",
    response_model=BrokerCapabilitiesResponse,
    summary="Broker capability matrix used by execution router",
)
def get_broker_capabilities() -> BrokerCapabilitiesResponse:
    return BrokerCapabilitiesResponse(capabilities=execution_bridge.broker_capabilities())


@router.get(
    "/brokers/connections",
    response_model=BrokerConnectionsResponse,
    summary="Broker connection inventory for the connection safety banner",
)
def get_broker_connections(user: User = CurrentUser) -> BrokerConnectionsResponse:
    capability_map = execution_bridge.broker_capabilities()
    with get_session() as session:
        rows = session.execute(
            select(BrokerOAuthConnection).where(BrokerOAuthConnection.user_id == str(user.id))
        ).scalars().all()

    connections = {row.provider: row for row in rows}
    brokers: list[BrokerConnectionEntryResponse] = []

    for provider, capability in capability_map.items():
        connection = connections.get(provider)
        if provider == "alpaca":
            oauth_ready = bool(
                settings.alpaca_connect_client_id
                and settings.alpaca_connect_client_secret
                and settings.alpaca_connect_redirect_uri
            )
            connected = bool(connection and connection.connected and connection.access_token)
            brokers.append(
                BrokerConnectionEntryResponse(
                    provider=provider,
                    label="Alpaca",
                    connected=connected,
                    configured=False,
                    connectable=oauth_ready,
                    disconnect_supported=True,
                    auth_type="oauth",
                    permissions="Trading (User Authorized)" if connected else "Not Authorized",
                    mode="Paper Trading" if settings.alpaca_paper else "Live Trading",
                    status_label="Connected" if connected else ("Ready to Connect" if oauth_ready else "OAuth Not Configured"),
                    connect_path="/alpaca/oauth/start?next=/alpha",
                    disconnect_path="/alpaca/oauth/disconnect",
                    updated_at=connection.updated_at if connection else None,
                    last_error=connection.last_error if connection else None,
                    notes="Primary equities and crypto broker with user-authorized OAuth trading access.",
                    capabilities={
                        "supports_equities": bool(capability.get("supports_equities")),
                        "supports_crypto": bool(capability.get("supports_crypto")),
                        "supports_options": bool(capability.get("supports_options")),
                        "supports_fractional": bool(capability.get("supports_fractional")),
                        "supports_leverage": bool(capability.get("supports_leverage")),
                    },
                )
            )
            continue

        connected = bool(connection and connection.connected and connection.access_token)
        coinbase_keys_present = bool(settings.coinbase_api_key_name and settings.coinbase_api_private_key)
        if provider == "coinbase":
            coinbase_live_enabled = bool(settings.coinbase_live_trading_enabled)
            brokers.append(
                BrokerConnectionEntryResponse(
                    provider=provider,
                    label="Coinbase",
                    connected=False,
                    configured=coinbase_keys_present,
                    connectable=False,
                    disconnect_supported=False,
                    auth_type="api_key",
                    permissions=(
                        "Platform API Key Configured"
                        if coinbase_keys_present
                        else "API Key Not Configured"
                    ),
                    mode="Live Trading" if coinbase_live_enabled else "Configured but Disabled",
                    status_label=(
                        "Platform Configured"
                        if coinbase_keys_present and coinbase_live_enabled
                        else "Configured (Disabled by Env)"
                        if coinbase_keys_present
                        else "Not Configured"
                    ),
                    connect_path=None,
                    disconnect_path=None,
                    updated_at=connection.updated_at if connection else None,
                    last_error=connection.last_error if connection else None,
                    notes=(
                        "Coinbase is configured at the platform level via backend API keys. It is available for routed crypto execution, but it is not a user-authorized personal broker connection."
                        if coinbase_keys_present and coinbase_live_enabled
                        else "Coinbase keys are configured, but COINBASE_LIVE_TRADING_ENABLED is false."
                        if coinbase_keys_present
                        else "Add COINBASE_API_KEY_NAME and COINBASE_API_PRIVATE_KEY in backend environment variables."
                    ),
                    capabilities={
                        "supports_equities": bool(capability.get("supports_equities")),
                        "supports_crypto": bool(capability.get("supports_crypto")),
                        "supports_options": bool(capability.get("supports_options")),
                        "supports_fractional": bool(capability.get("supports_fractional")),
                        "supports_leverage": bool(capability.get("supports_leverage")),
                    },
                )
            )
            continue

        if capability.get("planned"):
            brokers.append(
                BrokerConnectionEntryResponse(
                    provider=provider,
                    label=capability.get("label") or provider.replace("_", " ").title(),
                    connected=False,
                    configured=False,
                    planned=True,
                    connectable=False,
                    disconnect_supported=False,
                    auth_type="planned",
                    permissions="OAuth Application Pending",
                    mode=None,
                    status_label="Integration Planned",
                    connect_path=None,
                    disconnect_path=None,
                    oauth_url=capability.get("oauth_url"),
                    updated_at=None,
                    last_error=None,
                    notes=capability.get("notes") or f"OAuth integration is planned. Apply at {capability.get('oauth_url', 'the broker developer portal')}.",
                    capabilities={
                        "supports_equities": bool(capability.get("supports_equities")),
                        "supports_crypto": bool(capability.get("supports_crypto")),
                        "supports_options": bool(capability.get("supports_options")),
                        "supports_fractional": bool(capability.get("supports_fractional")),
                        "supports_leverage": bool(capability.get("supports_leverage")),
                    },
                )
            )
            continue

        brokers.append(
            BrokerConnectionEntryResponse(
                provider=provider,
                label=provider.replace("_", " ").title(),
                connected=connected,
                configured=False,
                planned=False,
                connectable=False,
                disconnect_supported=False,
                auth_type="unavailable",
                permissions="Activation Pending",
                mode=None,
                status_label="Not Yet Activated",
                connect_path=None,
                disconnect_path=None,
                updated_at=connection.updated_at if connection else None,
                last_error=connection.last_error if connection else None,
                notes="Broker is visible in the routing layer, but account authentication has not been implemented yet.",
                capabilities={
                    "supports_equities": bool(capability.get("supports_equities")),
                    "supports_crypto": bool(capability.get("supports_crypto")),
                    "supports_options": bool(capability.get("supports_options")),
                    "supports_fractional": bool(capability.get("supports_fractional")),
                    "supports_leverage": bool(capability.get("supports_leverage")),
                },
            )
        )

    return BrokerConnectionsResponse(brokers=brokers)


@router.get(
    "/news/sources",
    response_model=NewsSourceWhitelistResponse,
    summary="Whitelisted public news sources used by the news intelligence layer",
)
def get_news_sources() -> NewsSourceWhitelistResponse:
    return NewsSourceWhitelistResponse(sources=news_intelligence.source_whitelist())


@router.get(
    "/news/stream/status",
    summary="Coinbase websocket ingest status for live news/momentum augmentation",
)
def get_news_stream_status() -> dict:
    return coinbase_ws_service.status()


@router.get(
    "/news/audit",
    response_model=NewsAuditResponse,
    summary="Recent news-signal audit entries for traceability",
)
def get_news_audit(limit: int = Query(default=50, ge=1, le=500)) -> NewsAuditResponse:
    entries = news_intelligence.recent_audit(limit=limit)
    return NewsAuditResponse(entries=[NewsAuditEntryResponse(**item) for item in entries])


@router.get(
    "/news/{symbol}",
    response_model=NewsSignalResponse,
    summary="News and event signal for a symbol from public sources",
)
def get_news_signal(symbol: str) -> NewsSignalResponse:
    return NewsSignalResponse(**news_intelligence.analyze_symbol(symbol))


@router.get(
    "/context/{symbol}",
    response_model=ContextSignalResponse,
    summary="Context intelligence for a symbol (news/sentiment/event modifiers)",
)
def get_context_signal(symbol: str) -> ContextSignalResponse:
    return ContextSignalResponse(**context_intelligence.get_context(symbol))


@router.get(
    "/audit/decisions",
    response_model=DecisionAuditSummaryListResponse,
    summary="List recent persisted decision audits",
)
def list_decision_audits(
    limit: int = Query(default=50, ge=1, le=200),
    symbol: str | None = Query(default=None),
    status: str | None = Query(default=None),
) -> DecisionAuditSummaryListResponse:
    rows = decision_audit_store.list_recent(limit=limit, symbol=symbol, status=status)
    return DecisionAuditSummaryListResponse(entries=[DecisionAuditSummaryResponse(**row) for row in rows])


@router.get(
    "/audit/decisions/{audit_id}",
    response_model=DecisionAuditDetailResponse,
    summary="Get full decision audit payload by audit id",
)
def get_decision_audit(audit_id: str) -> DecisionAuditDetailResponse:
    row = decision_audit_store.get_by_id(audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Decision audit not found: {audit_id}")
    return DecisionAuditDetailResponse(**row)


@router.get(
    "/audit/replay/{audit_id}",
    response_model=DecisionReplayResponse,
    summary="Replay a decision step-by-step from persisted lineage",
)
def get_decision_replay(audit_id: str) -> DecisionReplayResponse:
    row = decision_audit_store.get_by_id(audit_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Decision audit not found: {audit_id}")

    explainability = row.get("explainability_snapshot") or {}
    replay_steps = [
        DecisionReplayStepResponse(
            stage="CONTEXT",
            title="Context Inputs",
            summary="News/sentiment/event inputs after validation and correlation checks.",
            payload=row.get("context_snapshot") or {},
        ),
        DecisionReplayStepResponse(
            stage="ALLOCATION",
            title="Allocation Decision",
            summary="Sizing and notional recommendation after allocator + constraints.",
            payload=row.get("allocation_snapshot") or {},
        ),
        DecisionReplayStepResponse(
            stage="GOVERNOR",
            title="Risk Governor",
            summary="Portfolio-level override layer (allow/resize/block).",
            payload=row.get("governor_snapshot") or {},
        ),
        DecisionReplayStepResponse(
            stage="EXECUTION",
            title="Execution Result",
            summary="Final action submitted (or rejected) with execution details.",
            payload=row.get("execution_snapshot") or {},
        ),
        DecisionReplayStepResponse(
            stage="EXPLAINABILITY",
            title="Explainability Envelope",
            summary="Human-readable reasoning and safeguards used for traceability.",
            payload=explainability,
        ),
    ]

    why_not: list[str] = []
    if row.get("status") != "ACCEPTED":
        reason = str((row.get("execution_snapshot") or {}).get("reason") or "").strip()
        if reason:
            why_not.append(reason)
        exp_reason = str(explainability.get("reasoning") or "").strip()
        if exp_reason and exp_reason not in why_not:
            why_not.append(exp_reason)

    return DecisionReplayResponse(
        audit_id=row["audit_id"],
        symbol=row["symbol"],
        decision_type=row["decision_type"],
        status=row["status"],
        generated_at=row["timestamp"],
        replay_steps=replay_steps,
        why_not=why_not,
    )


@router.post(
    "/goal",
    response_model=GoalStatusResponse,
    summary="Set target-based goal for pressure-aware allocation",
)
def set_goal(payload: GoalTargetRequest) -> GoalStatusResponse:
    status = goal_engine.configure(
        start_capital=payload.start_capital,
        target_capital=payload.target_capital,
        timeframe_days=payload.timeframe_days,
    )
    return GoalStatusResponse(**status)


@router.get(
    "/goal/status",
    response_model=GoalStatusResponse,
    summary="Get current target trajectory and pressure state",
)
def get_goal_status() -> GoalStatusResponse:
    portfolio = portfolio_manager.snapshot()
    status = goal_engine.status(current_capital=float(portfolio["account_balance"]))
    return GoalStatusResponse(**status)


@router.get(
    "/opportunities",
    response_model=OpportunitiesResponse,
    summary="Top opportunity scan with risk-adjusted allocation recommendations",
)
def get_opportunities(limit: int = Query(default=10, ge=1, le=25)) -> OpportunitiesResponse:
    portfolio = portfolio_manager.snapshot()
    control = control_engine.status()
    goal = goal_engine.status(current_capital=float(portfolio["account_balance"]))

    result = opportunity_scanner.scan(
        limit=limit,
        account_balance=float(portfolio["account_balance"]),
        drawdown_pct=float(control["rolling_drawdown_pct"]),
        current_exposure_pct=float(portfolio["risk_exposure_pct"]),
        goal_pressure_multiplier=float(goal["goal_pressure_multiplier"]),
    )

    return OpportunitiesResponse(
        scanned=result["scanned"],
        passed_prefilter=result["passed_prefilter"],
        opportunities=[OpportunityRecommendation(**item) for item in result["opportunities"]],
        capital_allocation_recommendations=[
            CapitalSplitRecommendation(**item) for item in result["capital_allocation_recommendations"]
        ],
        goal=GoalStatusResponse(**goal),
    )


@router.get(
    "/weights",
    response_model=AgentWeightsResponse,
    summary="Current dynamic agent weights across all market regimes",
)
def get_agent_weights() -> AgentWeightsResponse:
    all_regime_weights = dynamic_weight_engine.get_all_regime_weights()
    # Convert nested dicts to list of AgentWeightEntry per regime
    regime_map: dict[str, list[AgentWeightEntry]] = {}
    for regime, weights in all_regime_weights.items():
        # Raw scores use the same weight values for display when no settled history yet
        regime_map[regime] = [
            AgentWeightEntry(agent_name=agent, weight=w, raw_score=round(w * 3 - 1.0, 4))
            for agent, w in weights.items()
        ]
    return AgentWeightsResponse(regime_weights=regime_map)


@router.get(
    "/weights/history",
    response_model=AgentWeightHistoryResponse,
    summary="Weight snapshot history (post-outcome updates)",
)
def get_weight_history(
    limit: int = Query(default=100, ge=1, le=500),
) -> AgentWeightHistoryResponse:
    snapshots = dynamic_weight_engine.get_weight_history(n=limit)
    result: list[AgentWeightSnapshot] = []
    for snap in snapshots:
        entries = [
            AgentWeightEntry(
                agent_name=agent,
                weight=w,
                raw_score=snap.raw_scores.get(agent, 0.0),
            )
            for agent, w in snap.weights.items()
        ]
        result.append(
            AgentWeightSnapshot(
                cycle_id=snap.cycle_id,
                timestamp=snap.timestamp,
                regime=snap.regime,
                weights=entries,
            )
        )
    return AgentWeightHistoryResponse(
        snapshots=result,
        total_settled_cycles=len(snapshots),
    )


@router.get(
    "/decisions",
    response_model=SwarmDecisionListResponse,
    summary="Recent agent swarm decisions (newest first)",
)
def get_decisions(
    limit: int = Query(default=50, ge=1, le=200),
) -> SwarmDecisionListResponse:
    records = swarm_decision_store.get_recent(n=limit)
    decisions = [_to_response(r) for r in reversed(records)]  # newest first
    return SwarmDecisionListResponse(
        decisions=decisions,
        total_cycles=swarm_decision_store.total_cycles,
    )


@router.get(
    "/execution-history",
    response_model=ExecutionHistoryResponse,
    summary="Recent execution and allocation journal",
)
def get_execution_history(limit: int = Query(default=50, ge=1, le=200)) -> ExecutionHistoryResponse:
    entries = execution_journal.recent(limit)
    return ExecutionHistoryResponse(
        executions=[
            ExecutionHistoryEntry(
                execution_id=item.execution_id,
                cycle_id=item.cycle_id,
                symbol=item.symbol,
                regime=item.regime,
                action=item.action,
                strategy=item.strategy,
                confidence=item.confidence,
                risk_level=item.risk_level,
                allocation_pct=item.allocation_pct,
                qty=item.qty,
                notional=item.notional,
                mode=item.mode,
                submitted=item.submitted,
                order_id=item.order_id,
                reason=item.reason,
                error=item.error,
                timestamp=item.timestamp,
                outcome_label=item.outcome_label,
                pnl=item.pnl,
            )
            for item in reversed(entries)
        ]
    )


@router.post(
    "/run-cycle",
    response_model=SwarmCycleResponse,
    summary="Run one full agent swarm decision cycle",
    description=(
        "Runs all agents against the supplied market data, aggregates their signals "
        "via weighted confidence voting, applies the risk agent veto gate, then "
        "submits the final action to Alpaca (paper trading). All decisions are "
        "logged to the swarm decision store and returned in the response."
    ),
)
def run_cycle(payload: SwarmCycleRequest, request: Request) -> SwarmCycleResponse:
    record = swarm_manager.run_cycle(
        symbol=payload.symbol,
        close_prices=payload.close_prices,
        volumes=payload.volumes,
        regime=payload.regime,
        regime_confidence=payload.regime_confidence,
        default_qty=payload.qty,
    )
    record.request_id = getattr(request.state, "request_id", "") or request.headers.get("x-request-id", "")
    return _to_response(record)


@router.post(
    "/decisions/{cycle_id}/outcome",
    response_model=SwarmCycleResponse,
    summary="Attach entry/exit outcome and attribution to a swarm cycle",
)
def update_decision_outcome(cycle_id: str, payload: DecisionOutcomeUpdateRequest) -> SwarmCycleResponse:
    updated = swarm_decision_store.update_outcome(
        cycle_id=cycle_id,
        entry_price=payload.entry_price,
        exit_price=payload.exit_price,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail=f"Cycle not found: {cycle_id}")
    return _to_response(updated)


# ---------------------------------------------------------------------------
# Future WebSocket hook — uncomment when ready to stream live decisions
# ---------------------------------------------------------------------------
# from fastapi import WebSocket
# from fastapi.websockets import WebSocketDisconnect
#
# @router.websocket("/ws/agents/live")
# async def ws_agent_live(websocket: WebSocket) -> None:
#     """Stream live swarm decisions to connected clients."""
#     await websocket.accept()
#     last_seen = swarm_decision_store.total_cycles
#     try:
#         while True:
#             current = swarm_decision_store.total_cycles
#             if current > last_seen:
#                 record = swarm_decision_store.get_latest()
#                 if record:
#                     await websocket.send_json(_to_response(record).model_dump(mode="json"))
#                 last_seen = current
#             await asyncio.sleep(0.5)
#     except WebSocketDisconnect:
#         pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_response(r) -> SwarmCycleResponse:  # type: ignore[return]
    return SwarmCycleResponse(
        cycle_id=r.cycle_id,
        request_id=r.request_id,
        symbol=r.symbol,
        timestamp=r.timestamp,
        regime=r.regime,
        agent_signals=[
            SwarmAgentSignal(
                agent_name=s["agent_name"],
                action=s["action"],
                confidence=s["confidence"],
                reasoning=s["reasoning"],
            )
            for s in r.agent_signals
        ],
        final_action=r.final_action,
        final_confidence=r.final_confidence,
        consensus_reasoning=r.consensus_reasoning,
        execution_submitted=r.execution_submitted,
        execution_result=r.execution_result,
        vetoed=r.vetoed,
        veto_reason=r.veto_reason or "",
        governor_decision=((r.execution_result or {}).get("explainability", {}).get("inputs", {}).get("governor", {}).get("decision")),
        governor_reason=((r.execution_result or {}).get("explainability", {}).get("inputs", {}).get("governor", {}).get("reason")),
        explainability=(r.execution_result or {}).get("explainability"),
        allocation=AllocationDecision(**r.allocation) if r.allocation else None,
        outcome=DecisionOutcome(**r.outcome) if r.outcome else None,
        agent_attribution=[AgentAttribution(**item) for item in (r.agent_attribution or [])],
    )
