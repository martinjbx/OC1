#!/usr/bin/env python3
"""
Daily screener runner
Executes the stock screener and sends Telegram alert
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from screener import run_daily_screen, format_report

def main():
    print("=" * 60)
    print("RUNNING DAILY STOCK SCREENER")
    print("S&P 500 + Nasdaq 100 + FTSE 100")
    print("=" * 60)
    
    # Run screen on all available tickers
    results = run_daily_screen(save_to_db=True, max_tickers=None)
    
    # Format report
    report = format_report(results)
    print("\n" + report)
    
    # TODO: Send to Telegram via OpenClaw message tool
    # For now, just print
    print("\n✅ Screening complete!")

if __name__ == "__main__":
    main()
