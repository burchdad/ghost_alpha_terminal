import sys
import os
import traceback

# Setup paths
sys.path.append(os.getcwd())

from app.api.routes.options import SUPPORTED_STRATEGIES
from app.models.schemas import OptionsExecutionRequest
from app.services.options_execution_service import options_execution_service
from app.services.tradier_client import tradier_client
from app.core.config import settings

def get_bias(strategy_name):
    strategy = strategy_name.lower()
    if any(s in strategy for s in ['condor', 'straddle', 'strangle', 'butterfly']):
        return 'NEUTRAL'
    if 'put' in strategy:
        return 'BEARISH'
    return 'BULLISH'

def run_test():
    print("--- Environment State ---")
    try:
        print(f"Tradier Configured: {tradier_client.is_configured()}")
    except Exception as e:
        print(f"Tradier Configured: Error ({e})")
    
    print(f"Tradier Sandbox: {getattr(settings, 'tradier_sandbox', 'N/A')}")
    print(f"Tradier Live Trading Enabled: {getattr(settings, 'tradier_live_trading_enabled', 'N/A')}")
    print("-------------------------\n")

    results = []

    for strategy in SUPPORTED_STRATEGIES:
        bias = get_bias(strategy)
        
        # Check if bias is a field in OptionsExecutionRequest
        payload = {
            'symbol': 'SPY',
            'strategy': strategy,
            'quantity': 1,
            'preview': False
        }
        
        # Try to add bias, if it fails validation we'll fall back
        try:
            request = OptionsExecutionRequest(**payload, bias=bias)
        except Exception:
            request = OptionsExecutionRequest(**payload)

        res_entry = {
            'strategy': strategy,
            'approved': False,
            'order_class': None,
            'legs_count': 0,
            'risk_level': None,
            'reason': None,
            'order_id': None,
            'order_status': None,
            'exception': None
        }

        try:
            response = options_execution_service.preview_or_execute(request)
            if isinstance(response, dict):
                res_entry['approved'] = response.get('approved', False)
                res_entry['order_class'] = response.get('order_class')
                res_entry['legs_count'] = len(response.get('legs', []))
                res_entry['risk_level'] = response.get('risk_level')
                res_entry['reason'] = response.get('reason')
                
                order_resp = response.get('order_response')
                if order_resp and isinstance(order_resp, dict):
                    res_entry['order_id'] = order_resp.get('id') or order_resp.get('order_id')
                    res_entry['order_status'] = order_resp.get('status')
            else:
                res_entry['reason'] = f"Unexpected response type: {type(response)}"
        except Exception as e:
            res_entry['exception'] = f"{type(e).__name__}: {str(e)}"

        results.append(res_entry)

    # Print Table
    header = f"{'Strategy':<20} | {'Appr':<5} | {'Class':<10} | {'Legs':<4} | {'Risk':<6} | {'Order ID':<10} | {'Status':<10} | {'Err'}"
    print(header)
    print("-" * len(header))
    
    counts = {'total': 0, 'submitted': 0, 'approved_no_sub': 0, 'blocked': 0, 'exceptions': 0}
    
    for r in results:
        counts['total'] += 1
        if r['exception']:
            counts['exceptions'] += 1
            err_msg = r['exception'][:50]
        else:
            err_msg = r['reason'] if not r['approved'] and r['reason'] else ""
            if r['order_id']:
                counts['submitted'] += 1
            elif r['approved']:
                counts['approved_no_sub'] += 1
            else:
                counts['blocked'] += 1

        print(f"{r['strategy']:<20} | {str(r['approved']):<5} | {str(r['order_class']):<10} | {str(r['legs_count']):<4} | {str(r['risk_level']):<6} | {str(r['order_id']):<10} | {str(r['order_status']):<10} | {err_msg}")

    print("\n--- Summary ---")
    print(f"Total: {counts['total']}")
    print(f"Submitted w/ Order Response: {counts['submitted']}")
    print(f"Approved w/o Submission: {counts['approved_no_sub']}")
    print(f"Blocked: {counts['blocked']}")
    print(f"Exceptions: {counts['exceptions']}")

if __name__ == '__main__':
    run_test()
