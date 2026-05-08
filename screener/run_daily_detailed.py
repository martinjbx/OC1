#!/usr/bin/env python3
"""
Run daily screener with detailed reporting showing confluence breakdown
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from screener import run_daily_screen, format_report

if __name__ == "__main__":
    print("=" * 60)
    print("RUNNING S&P 500 SCREENER - DETAILED MODE")
    print("=" * 60)
    
    # Run with all filters
    print("\n1️⃣  FULL CONFLUENCE (SMMA + RSI + ADX)")
    print("-" * 60)
    results_full = run_daily_screen(save_to_db=True, max_tickers=150, require_rsi=True, require_adx=True)
    print(format_report(results_full))
    
    # Run with RSI only (no ADX requirement)
    print("\n\n2️⃣  SMMA + RSI ONLY (ADX informational)")
    print("-" * 60)
    results_rsi = run_daily_screen(save_to_db=False, max_tickers=150, require_rsi=True, require_adx=False)
    print(format_report(results_rsi))
    
    # Run with ADX only (no RSI requirement)
    print("\n\n3️⃣  SMMA + ADX ONLY (RSI informational)")
    print("-" * 60)
    results_adx = run_daily_screen(save_to_db=False, max_tickers=150, require_rsi=False, require_adx=True)
    print(format_report(results_adx))
    
    # Summary
    print("\n\n" + "=" * 60)
    print("📊 CONFLUENCE SUMMARY")
    print("=" * 60)
    print(f"Full confluence (SMMA+RSI+ADX): {len(results_full['buy_signals'])} signals")
    print(f"SMMA + RSI only:                {len(results_rsi['buy_signals'])} signals")
    print(f"SMMA + ADX only:                {len(results_adx['buy_signals'])} signals")
    print("=" * 60)
