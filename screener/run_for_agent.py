#!/usr/bin/env python3
"""
Agent-friendly screener runner
Outputs results that OpenClaw agent can forward to Telegram
Use this when running via agent commands or subagents
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from screener import run_daily_screen
from telegram_report import format_telegram_report, should_send_report, format_summary_report


def main():
    # Run silently (minimal logging to stdout)
    results = run_daily_screen(
        save_to_db=True,
        max_tickers=None,
        require_rsi=True,
        require_adx=False
    )
    
    # Determine if we should send
    has_signals = should_send_report(results, send_empty=False)
    
    if has_signals:
        # Format and output message
        message = format_telegram_report(results, detailed=False)
        
        # Output with clear markers for agent to detect
        print("\n" + "=" * 60)
        print("TELEGRAM_MESSAGE_START")
        print("=" * 60)
        print(message)
        print("=" * 60)
        print("TELEGRAM_MESSAGE_END")
        print("=" * 60)
    else:
        # No signals - output summary
        summary = format_summary_report(results)
        print(f"\n{summary}")
        print("(No signals detected - skipping Telegram report)")


if __name__ == "__main__":
    main()
