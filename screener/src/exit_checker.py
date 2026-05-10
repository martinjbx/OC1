#!/usr/bin/env python3
"""
Minervini Exit Signal Checker
Monitors candidates from the watchlist for exit signals:
  - Primary: Close below 50-day MA
  - Confirmation: Volume on that day > 1.5x 20-day average volume

Watchlist is persisted in dashboard/data/watchlist.json
Exit alerts are written to dashboard/data/exit_alerts.json
"""

import json
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')


DATA_DIR = Path(__file__).parent.parent / "dashboard" / "data"
WATCHLIST_FILE = DATA_DIR / "watchlist.json"
EXIT_ALERTS_FILE = DATA_DIR / "exit_alerts.json"


def load_watchlist() -> dict:
    """Load persisted watchlist, or return empty structure."""
    if WATCHLIST_FILE.exists():
        with open(WATCHLIST_FILE) as f:
            return json.load(f)
    return {"tickers": {}, "last_updated": None}


def save_watchlist(watchlist: dict):
    """Persist watchlist to disk."""
    watchlist["last_updated"] = datetime.utcnow().isoformat()
    with open(WATCHLIST_FILE, "w") as f:
        json.dump(watchlist, f, indent=2)


def update_watchlist_from_scan(watchlist: dict, candidates: list) -> int:
    """
    Add new candidates (7+ criteria) to watchlist.
    Returns count of newly added tickers.
    """
    added = 0
    today = date.today().isoformat()
    for c in candidates:
        ticker = c["ticker"]
        if ticker not in watchlist["tickers"]:
            watchlist["tickers"][ticker] = {
                "date_added": today,
                "entry_price": c.get("price"),
                "rs_rating": c.get("rs_rating"),
                "criteria_passed": c.get("criteria_passed"),
                "exited": False,
                "exit_date": None,
                "exit_reason": None,
            }
            added += 1
        else:
            # Update criteria/RS in case it improved
            watchlist["tickers"][ticker]["criteria_passed"] = c.get("criteria_passed")
            watchlist["tickers"][ticker]["rs_rating"] = c.get("rs_rating")
    return added


def check_exit_signal(ticker: str, entry_price: float = None) -> dict:
    """
    Check a single ticker for exit signals.
    Returns a dict with signal info.
    """
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1y")

        if data is None or len(data) < 60:
            return {"ticker": ticker, "error": "insufficient_data"}

        # Calculate 50-day MA
        data["MA_50"] = data["Close"].rolling(window=50).mean()

        # Calculate 20-day average volume
        data["Vol_20avg"] = data["Volume"].rolling(window=20).mean()

        current_price = float(data["Close"].iloc[-1])
        ma_50 = float(data["MA_50"].iloc[-1])
        current_vol = float(data["Volume"].iloc[-1])
        avg_vol = float(data["Vol_20avg"].iloc[-1])

        # Previous close (to check if we just crossed under)
        prev_price = float(data["Close"].iloc[-2])
        prev_ma_50 = float(data["MA_50"].iloc[-2])

        below_ma50 = current_price < ma_50
        just_crossed_under = below_ma50 and (prev_price >= prev_ma_50)
        vol_elevated = (avg_vol > 0) and (current_vol > 1.5 * avg_vol)

        # Compute % above/below MA50
        pct_vs_ma50 = ((current_price / ma_50) - 1) * 100 if ma_50 > 0 else 0

        # P&L vs entry
        pnl_pct = None
        if entry_price and entry_price > 0:
            pnl_pct = round(((current_price / entry_price) - 1) * 100, 1)

        # Determine exit signal level
        if just_crossed_under and vol_elevated:
            signal = "STRONG_EXIT"          # Crossed under on heavy volume — act now
        elif just_crossed_under:
            signal = "WEAK_EXIT"            # Crossed under but volume not elevated — caution
        elif below_ma50:
            signal = "ALREADY_BELOW_MA50"   # Lingering below MA50 — monitor
        else:
            signal = "HOLD"

        return {
            "ticker": ticker,
            "signal": signal,
            "current_price": round(current_price, 2),
            "ma_50": round(ma_50, 2),
            "pct_vs_ma50": round(pct_vs_ma50, 2),
            "below_ma50": below_ma50,
            "just_crossed_under": just_crossed_under,
            "vol_ratio": round(current_vol / avg_vol, 2) if avg_vol > 0 else None,
            "vol_elevated": vol_elevated,
            "entry_price": entry_price,
            "pnl_pct": pnl_pct,
        }

    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def run_exit_check(candidates: list = None, max_workers: int = 10) -> dict:
    """
    Main entry point.
    - Loads watchlist
    - Optionally adds new candidates from today's Minervini scan
    - Checks all active (non-exited) watchlist entries for exit signals
    - Persists updated watchlist
    - Returns exit alert payload
    """
    watchlist = load_watchlist()

    # Add new scan candidates to watchlist
    newly_added = 0
    if candidates:
        newly_added = update_watchlist_from_scan(watchlist, candidates)
        print(f"  Watchlist: {newly_added} new tickers added, {len(watchlist['tickers'])} total")

    # Active tickers only
    active = {
        t: info for t, info in watchlist["tickers"].items()
        if not info.get("exited", False)
    }

    if not active:
        print("  Watchlist is empty — no exit checks to run.")
        save_watchlist(watchlist)
        return _empty_result()

    print(f"  Checking {len(active)} active watchlist tickers for exit signals...")

    # Parallel check
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(check_exit_signal, ticker, info.get("entry_price")): ticker
            for ticker, info in active.items()
        }
        for i, future in enumerate(as_completed(futures), 1):
            ticker = futures[future]
            try:
                result = future.result()
                result["date_added"] = active[ticker].get("date_added")
                results.append(result)
            except Exception as e:
                results.append({"ticker": ticker, "error": str(e)})
            if i % 20 == 0:
                print(f"    Progress: {i}/{len(active)}")

    # Categorise
    strong_exits = [r for r in results if r.get("signal") == "STRONG_EXIT"]
    weak_exits   = [r for r in results if r.get("signal") == "WEAK_EXIT"]
    below_ma50   = [r for r in results if r.get("signal") == "ALREADY_BELOW_MA50"]
    holds        = [r for r in results if r.get("signal") == "HOLD"]
    errors       = [r for r in results if "error" in r]

    # Mark strong exits in watchlist
    today = date.today().isoformat()
    for r in strong_exits:
        if r["ticker"] in watchlist["tickers"]:
            watchlist["tickers"][r["ticker"]]["exited"] = True
            watchlist["tickers"][r["ticker"]]["exit_date"] = today
            watchlist["tickers"][r["ticker"]]["exit_reason"] = "MA50_CROSS_HIGH_VOL"

    # Sort by pct below MA50 (most extended first)
    for group in (strong_exits, weak_exits, below_ma50):
        group.sort(key=lambda x: x.get("pct_vs_ma50", 0))

    save_watchlist(watchlist)

    return {
        "check_date": datetime.utcnow().isoformat(),
        "watchlist_size": len(watchlist["tickers"]),
        "active_positions": len(active),
        "newly_added": newly_added,
        "strong_exits": strong_exits,      # Crossed under MA50 + heavy vol → SELL
        "weak_exits": weak_exits,          # Crossed under MA50, normal vol → CAUTION
        "below_ma50_lingering": below_ma50, # Already below MA50 → MONITOR
        "holds": len(holds),
        "errors": len(errors),
    }


def _empty_result() -> dict:
    return {
        "check_date": datetime.utcnow().isoformat(),
        "watchlist_size": 0,
        "active_positions": 0,
        "newly_added": 0,
        "strong_exits": [],
        "weak_exits": [],
        "below_ma50_lingering": [],
        "holds": 0,
        "errors": 0,
    }
