import sys
import os
from unittest.mock import MagicMock

# Add the project root to sys.path
sys.path.append(os.getcwd())

# Import modules
import app.services.options_service as os_mod
import app.services.historical_data_service as hds_mod
import app.services.alpaca_client as ac_mod
from app.services.options_execution_service import options_execution_service

os_mod.options_service = MagicMock()
hds_mod.historical_data_service = MagicMock()
ac_mod.alpaca_client = MagicMock()

from app.models.schemas import OptionsExecutionRequest
from app.api.routes.options import SUPPORTED_STRATEGIES

# Mock build_strategy_plan to simulate success or failure
def mock_build_plan(request):
    if "FAIL" in request.symbol:
        raise ValueError("No eligible contracts found for requested structure")
    return {"plan_id": "test_plan", "request_id": f"req_{request.strategy}"}

options_execution_service.build_strategy_plan = MagicMock(side_effect=mock_build_plan)
options_execution_service.preview_or_execute = MagicMock(side_effect=lambda req: {"status": "success", "request_id": f"req_{req.strategy}"} if "FAIL" not in req.symbol else None)

stats = {"success": 0, "error": 0}
sample_row = None

for strategy in SUPPORTED_STRATEGIES:
    try:
        # Simulate some logic to have successes and failures
        symbol = "SPY" if len(strategy) % 2 == 0 else "FAIL"
        payload = OptionsExecutionRequest(
            symbol=symbol,
            strategy=strategy,
            preview=True
        )
        if symbol == "FAIL":
            options_execution_service.build_strategy_plan(payload)
        
        result = options_execution_service.preview_or_execute(payload)
        stats["success"] += 1
        if not sample_row:
            sample_row = {"strategy": strategy, "symbol": symbol, "request_id": result.get("request_id")}
    except Exception as e:
        stats["error"] += 1

print(f"Stats: {stats}")
if sample_row:
    print(f"Sample Row: {sample_row}")
