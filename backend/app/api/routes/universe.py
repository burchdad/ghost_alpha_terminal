"""
/universe — Dynamic ticker universe endpoints

GET /universe/symbols  → current equity universe (symbols + source metadata)
"""
from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter

from app.services.dynamic_universe_service import dynamic_universe_service

router = APIRouter(prefix="/universe", tags=["universe"])


@router.get("/symbols")
def get_universe_symbols() -> dict:
    snapshot = dynamic_universe_service.get_equity_symbols()
    return {
        "symbols": snapshot.symbols,
        "count": len(snapshot.symbols),
        "source_counts": snapshot.source_counts,
        "generated_at": snapshot.generated_at.isoformat(),
    }
