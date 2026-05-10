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


def check_take_profit(ticker: str, entry_price: float = None) -> dict:
    """
    Check Minervini-style take-profit conditions for a ticker.

    Rules (in priority order):
      1. Climactic / blowoff: 3+ consecutive wide-range days up on heavy volume
         AND stock >30% above 50-day MA → sell into strength immediately
      2. Extended above MA50: >25% above MA50 → partial profit zone
      3. 20-25% gain from entry price → target hit, take partial profits

    Returns a dict with take-profit signal info.
    """
    try:
        stock = yf.Ticker(ticker)
        data = stock.history(period="1y")

        if data is None or len(data) < 60:
            return {"ticker": ticker, "tp_signal": "NO_DATA"}

        data["MA_50"] = data["Close"].rolling(window=50).mean()
        data["Vol_20avg"] = data["Volume"].rolling(window=20).mean()
        data["day_range"] = data["High"] - data["Low"]
        data["avg_range"] = data["day_range"].rolling(window=20).mean()

        current_price = float(data["Close"].iloc[-1])
        ma_50 = float(data["MA_50"].iloc[-1])
        avg_vol = float(data["Vol_20avg"].iloc[-1])
        pct_above_ma50 = ((current_price / ma_50) - 1) * 100 if ma_50 > 0 else 0

        # --- 1. Climactic action detection ---
        climactic = False
        last3 = data.tail(3)
        wide_up_days = sum(
            1 for _, row in last3.iterrows()
            if row["Close"] > row["Open"]                          # up day
            and row["day_range"] > 1.5 * row["avg_range"]         # wide range
            and row["Volume"] > 1.5 * row["Vol_20avg"]            # heavy volume
        )
        if wide_up_days >= 2 and pct_above_ma50 > 25:
            climactic = True

        # --- 2. Extended above MA50 ---
        extended = pct_above_ma50 > 25

        # --- 3. Gain from entry ---
        gain_pct = None
        target_hit = False
        if entry_price and entry_price > 0:
            gain_pct = round(((current_price / entry_price) - 1) * 100, 1)
            target_hit = gain_pct >= 20

        # Determine signal
        if climactic:
            tp_signal = "CLIMACTIC_SELL"       # Sell most/all into strength now
        elif extended and target_hit:
            tp_signal = "PARTIAL_PROFIT"       # Take 1/3 to 1/2 off the table
        elif extended:
            tp_signal = "EXTENDED_WATCH"       # Getting stretched — watch closely
        elif target_hit:
            tp_signal = "TARGET_HIT"           # 20-25% gain reached — take partial
        else:
            tp_signal = "HOLD"

        return {
            "ticker": ticker,
            "tp_signal": tp_signal,
            "current_price": round(current_price, 2),
            "ma_50": round(ma_50, 2),
            "pct_above_ma50": round(pct_above_ma50, 2),
            "climactic": climactic,
            "wide_up_days": wide_up_days,
            "gain_pct": gain_pct,
            "entry_price": entry_price,
        }

    except Exception as e:
        return {"ticker": ticker, "tp_signal": "ERROR", "error": str(e)}


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

    # Parallel check — run exit + take-profit concurrently
    exit_results = []
    tp_results = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        exit_futures = {
            executor.submit(check_exit_signal, ticker, info.get("entry_price")): (ticker, "exit")
            for ticker, info in active.items()
        }
        tp_futures = {
            executor.submit(check_take_profit, ticker, info.get("entry_price")): (ticker, "tp")
            for ticker, info in active.items()
        }
        all_futures = {**exit_futures, **tp_futures}

        for i, future in enumerate(as_completed(all_futures), 1):
            ticker, kind = all_futures[future]
            try:
                result = future.result()
                result["date_added"] = active[ticker].get("date_added")
                if kind == "exit":
                    exit_results.append(result)
                else:
                    tp_results.append(result)
            except Exception as e:
                pass
            if i % 40 == 0:
                print(f"    Progress: {i}/{len(active)*2}")

    # Categorise exits
    strong_exits = [r for r in exit_results if r.get("signal") == "STRONG_EXIT"]
    weak_exits   = [r for r in exit_results if r.get("signal") == "WEAK_EXIT"]
    below_ma50   = [r for r in exit_results if r.get("signal") == "ALREADY_BELOW_MA50"]
    holds        = [r for r in exit_results if r.get("signal") == "HOLD"]
    errors       = [r for r in exit_results if "error" in r]

    # Categorise take-profits
    climactic_sells  = [r for r in tp_results if r.get("tp_signal") == "CLIMACTIC_SELL"]
    partial_profits  = [r for r in tp_results if r.get("tp_signal") in ("PARTIAL_PROFIT", "TARGET_HIT")]
    extended_watch   = [r for r in tp_results if r.get("tp_signal") == "EXTENDED_WATCH"]

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
        # Exit signals
        "strong_exits": strong_exits,       # Crossed under MA50 + heavy vol → SELL
        "weak_exits": weak_exits,           # Crossed under MA50, normal vol → CAUTION
        "below_ma50_lingering": below_ma50, # Already below MA50 → MONITOR
        "holds": len(holds),
        "errors": len(errors),
        # Take-profit signals
        "climactic_sells": climactic_sells,  # Blowoff top → sell into strength now
        "partial_profits": partial_profits,  # 20-25% gain or extended → take partial
        "extended_watch": extended_watch,    # Getting stretched above MA50
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
        "climactic_sells": [],
        "partial_profits": [],
        "extended_watch": [],
    }
