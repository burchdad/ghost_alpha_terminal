from fastapi import APIRouter, Query

from app.models.schemas import AlpacaRequestIdEntry, AlpacaRequestIdsResponse
from app.services.request_id_store import request_id_store

router = APIRouter(prefix="/alpaca", tags=["alpaca"])


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
