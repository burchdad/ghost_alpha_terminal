from fastapi import APIRouter

from app.models.schemas import OptionsChainResponse
from app.services.options_service import options_service

router = APIRouter(prefix="/options", tags=["options"])


@router.get("/{symbol}", response_model=OptionsChainResponse)
def get_options(symbol: str) -> OptionsChainResponse:
    return options_service.get_options_chain(symbol=symbol)
