#!/usr/bin/env python3
"""
Structure Break + SMMA 15/29 Screener Runner
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from structure_screener import run_structure_screen, format_structure_report

def main():
    print("=" * 70)
    print("STRUCTURE BREAK + SMMA 15/29 SCREENER")
    print("Full ticker universe: S&P 500 + Nasdaq 100 + FTSE 100")
    print("=" * 70)
    
    # Run screen on all available tickers
    results = run_structure_screen(max_tickers=None, verbose=True)
    
    # Format report
    report = format_structure_report(results)
    print("\n" + report)
    
    print("\n✅ Screening complete!")
    
    return results

if __name__ == "__main__":
    results = main()
