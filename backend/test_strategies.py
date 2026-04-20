import asyncio
import traceback
import os
import sys

# Ensure current directory is in sys.path
sys.path.append(os.getcwd())

from app.models.schemas import OptionsExecutionRequest
from app.services.options_execution_service import options_execution_service

async def main():
    # Extracted from the validation error message
    strategies = ['LONG_CALL', 'LONG_PUT', 'VERTICAL_CALL'][:3]
    
    for strategy in strategies:
        print(f"Testing strategy: {strategy}")
        try:
            request = OptionsExecutionRequest(
                symbol='SPY',
                strategy=strategy,
                bias='BULLISH',
                quantity=1,
                preview=True
            )
            result = await options_execution_service.preview_or_execute(request)
            print(f"Result: {result}")
        except Exception as e:
            print(f"Exception for {strategy}: {repr(e)}")
            traceback.print_exc()
        print("-" * 40)

if __name__ == "__main__":
    asyncio.run(main())
