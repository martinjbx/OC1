#!/usr/bin/env python3
"""Test Telegram message formatting"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from screener import run_daily_screen
from telegram_report import format_telegram_report, should_send_report, format_summary_report

print("Testing Telegram message format with 50 tickers...\n")

# Run with limited tickers
results = run_daily_screen(
    save_to_db=False,
    max_tickers=50,
    require_rsi=True,
    require_adx=False
)

print("\n" + "=" * 60)
print("FORMATTED TELEGRAM MESSAGE:")
print("=" * 60)

if should_send_report(results, send_empty=False):
    message = format_telegram_report(results, detailed=False)
    print(message)
else:
    summary = format_summary_report(results)
    print(summary)
    print("\n(No signals - summary only)")

print("=" * 60)
