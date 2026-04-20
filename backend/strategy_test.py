import sys
import os
import unittest
from unittest.mock import MagicMock
from datetime import datetime

# Add the project root to sys.path
sys.path.append("/workspaces/ghost_alpha_terminal/backend")

# Import modules
import app.services.options_service as os_mod
import app.services.historical_data_service as hds_mod
import app.services.alpaca_client as ac_mod
from app.services.options_execution_service import options_execution_service

os_mod.options_service = MagicMock()
hds_mod.historical_data_service = MagicMock()
ac_mod.alpaca_client = MagicMock()

from app.models.schemas import OptionsChainResponse, OptionsExecutionRequest
from app.api.routes.options import SUPPORTED_STRATEGIES

# Mock build_strategy_plan to fail or return as if legs are missing
def mock_build_plan(request):
    if request.strategy.startswith("CUSTOM_") and not request.custom_legs:
        raise ValueError("Custom strategy requires at least one leg")
    # For others, simulate as if it worked or failed as before
    raise ValueError("No eligible contracts found for requested structure")

options_execution_service.build_strategy_plan = MagicMock(side_effect=mock_build_plan)

for strategy in SUPPORTED_STRATEGIES:
    try:
        payload = OptionsExecutionRequest(
            symbol="SPY",
            strategy=strategy,
            preview=True
        )
        result = options_execution_service.preview_or_execute(payload)
    except Exception as e:
        print(f"Strategy {strategy}: ERROR - {type(e).__name__}: {str(e)}")
