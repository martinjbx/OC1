#!/usr/bin/env python3
"""
Daily screener with Telegram reporting
Run via OpenClaw - uses message tool to send results
"""

import sys
import subprocess
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from screener import run_daily_screen
from telegram_report import format_telegram_report, should_send_report, format_summary_report


def send_telegram_message(message: str) -> bool:
    """
    Send message via OpenClaw message tool
    
    Args:
        message: Markdown-formatted message
    
    Returns:
        bool: Success status
    """
    try:
        # Try method 1: openclaw CLI (when running as cron job)
        result = subprocess.run(
            ['openclaw', 'message', 'send', '--channel', 'telegram', '--', message],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Message sent to Telegram")
            return True
        else:
            print(f"⚠️  CLI send failed: {result.stderr}")
            print("💡 If running from OpenClaw agent, use: message tool with action=send")
            return False
    
    except FileNotFoundError:
        print("⚠️  openclaw CLI not found in PATH")
        print("💡 If running from OpenClaw agent context, the agent will handle delivery")
        return False
    except Exception as e:
        print(f"❌ Error sending message: {e}")
        return False


def main():
    print("=" * 60)
    print("RUNNING DAILY SCREENER WITH TELEGRAM REPORTING")
    print("=" * 60)
    
    # Run the screen
    print("\nScreening all tickers...")
    results = run_daily_screen(
        save_to_db=True,
        max_tickers=None,
        require_rsi=True,
        require_adx=False
    )
    
    # Check if we should send a report
    send_full = should_send_report(results, send_empty=False)
    
    if send_full:
        # Send detailed report
        message = format_telegram_report(results, detailed=False)
        print("\n" + "=" * 60)
        print("SENDING TO TELEGRAM:")
        print("=" * 60)
        print(message)
        print("=" * 60)
        
        send_telegram_message(message)
    else:
        # No signals - send summary only
        summary = format_summary_report(results)
        print(f"\n{summary}")
        print("(No signals - skipping detailed report)")
        
        # Optional: uncomment to send "no signals" message
        # send_telegram_message(summary)
    
    print("\n✅ Screening complete!")


if __name__ == "__main__":
    main()
