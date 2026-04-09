"""
/orchestrator — GhostAlpha Intelligence Engine routes

GET  /orchestrator/status        → orchestrator state (auto mode, last scan, top pick)
POST /orchestrator/scan          → trigger a full market intelligence scan
GET  /orchestrator/scan/latest   → return last cached scan result (null if none)
POST /orchestrator/mode          → toggle auto / manual mode
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.models.schemas import (
    OrchestratorCandidateItem,
    OrchestratorModeRequest,
    OrchestratorModeResponse,
    OrchestratorScanResponse,
    OrchestratorStatusResponse,
)
from app.services.master_orchestrator import OrchestratorCandidate, master_orchestrator
from app.services.lightweight_metrics import lightweight_metrics

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


def _to_item(c: OrchestratorCandidate) -> OrchestratorCandidateItem:
    return OrchestratorCandidateItem(
        rank=c.rank,
        symbol=c.symbol,
        asset_class=c.asset_class,
        region=c.region,
        composite_score=c.composite_score,
        strategy_type=c.strategy_type,
        action_label=c.action_label,
        regime=c.regime,
        consensus_bias=c.consensus_bias,
        consensus_confidence=c.consensus_confidence,
        momentum_score=c.momentum_score,
        volume_spike=c.volume_spike,
        news_strength=c.news_strength,
        volatility=c.volatility,
        expected_return_pct=c.expected_return_pct,
        risk_level=c.risk_level,
        tradable=c.tradable,
        reasoning=c.reasoning,
    )


def _result_to_response(result) -> OrchestratorScanResponse:
    return OrchestratorScanResponse(
        candidates=[_to_item(c) for c in result.candidates],
        market_narrative=result.market_narrative,
        regime_summary=result.regime_summary,
        sector_leaders=result.sector_leaders,
        scanned_at=result.scanned_at,
        scan_count=result.scan_count,
        total_scanned=result.total_scanned,
        passed_prefilter=result.passed_prefilter,
        auto_mode=result.auto_mode,
    )


@router.get(
    "/status",
    response_model=OrchestratorStatusResponse,
    summary="GhostAlpha orchestrator state (auto mode, last scan, top pick)",
)
def get_orchestrator_status() -> OrchestratorStatusResponse:
    return OrchestratorStatusResponse(**master_orchestrator.status())


@router.post(
    "/scan",
    response_model=OrchestratorScanResponse,
    summary="Trigger a full market intelligence scan across all universe tickers",
)
def trigger_scan(
    limit: int = Query(default=15, ge=5, le=50),
) -> OrchestratorScanResponse:
    result = master_orchestrator.scan(limit=limit)
    try:
        lightweight_metrics.record_scan([c.strategy_type for c in result.candidates])
    except Exception:
        # Lightweight metrics should never interrupt scan availability.
        pass
    return _result_to_response(result)


@router.get(
    "/scan/latest",
    response_model=OrchestratorScanResponse | None,
    summary="Last cached market intelligence scan result (null if none triggered yet)",
)
def get_latest_scan() -> OrchestratorScanResponse | None:
    result = master_orchestrator.latest()
    if result is None:
        return None
    return _result_to_response(result)


@router.post(
    "/mode",
    response_model=OrchestratorModeResponse,
    summary="Set orchestrator auto / manual mode",
)
def set_mode(payload: OrchestratorModeRequest) -> OrchestratorModeResponse:
    master_orchestrator.set_auto_mode(
        enabled=payload.auto_mode,
        interval_seconds=payload.interval_seconds,
    )
    return OrchestratorModeResponse(**master_orchestrator.status())
