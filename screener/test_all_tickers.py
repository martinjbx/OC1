#!/usr/bin/env python3
"""Test screener with all unique tickers"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from screener import run_daily_screen, format_report

print('Testing with first 50 tickers...\n')
results = run_daily_screen(save_to_db=False, max_tickers=50, require_rsi=True, require_adx=False)

print('\n' + format_report(results))

print(f'\nBuy signals found: {len(results["buy_signals"])}')
if results['buy_signals']:
    for sig in results['buy_signals']:
        print(f'  - {sig["ticker"]}: ${sig["price"]:.2f}')
