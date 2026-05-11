#!/usr/bin/env python3
"""
Watchlist screener for Martin's personal watchlist.
Computes Minervini criteria + composite score + status for a fixed set of tickers.
"""

import yfinance as yf
import pandas as pd
from datetime import datetime

# Fixed personal watchlist
WATCHLIST = [
    {"display": "BTCUSD",  "yf": "BTC-USD",  "name": "Bitcoin"},
    {"display": "SOLUSD",  "yf": "SOL-USD",  "name": "Solana"},
    {"display": "ETHUSD",  "yf": "ETH-USD",  "name": "Ethereum"},
    {"display": "HYPEUSD", "yf": "HYPE-USD", "name": "Hyperliquid"},
    {"display": "TSLA",    "yf": "TSLA",     "name": "Tesla"},
    {"display": "NVDA",    "yf": "NVDA",     "name": "NVIDIA"},
    {"display": "GOOGL",   "yf": "GOOGL",    "name": "Alphabet"},
    {"display": "MSTR",    "yf": "MSTR",     "name": "MicroStrategy"},
    {"display": "MU",      "yf": "MU",       "name": "Micron"},
    {"display": "RKLB",    "yf": "RKLB",     "name": "Rocket Lab"},
    {"display": "MRVL",    "yf": "MRVL",     "name": "Marvell"},
    {"display": "FTC",     "yf": "FTC.L",    "name": "Filtronic"},
    {"display": "SPGP",    "yf": "SPGP",     "name": "iShares Gold Producers"},
    {"display": "URNP",    "yf": "URNP",     "name": "Sprott Uranium"},
    {"display": "UNFI",    "yf": "UNFI",     "name": "United Natural Foods"},
]

MIN_BARS = 100  # minimum bars for any useful analysis


def _no_data_entry(entry):
    """Return a zero/empty entry for a watchlist item with status NO_DATA."""
    return {
        "display": entry["display"],
        "yf_ticker": entry["yf"],
        "name": entry["name"],
        "status": "NO_DATA",
        "price": 0.0,
        "ma50": 0.0,
        "ma200": 0.0,
        "criteria_passed": 0,
        "rs_rating": 0,
        "pct_from_high": 0.0,
        "stock_return_1y": 0.0,
        "score": 0,
    }


def _compute_rs_rating(stock_return_1y, spy_return_1y):
    """Bin RS rating same as run_daily_json.py."""
    rel = stock_return_1y - spy_return_1y
    if rel > 50:
        return 95
    elif rel > 30:
        return 85
    elif rel > 15:
        return 75
    elif rel > 0:
        return 65
    elif rel > -15:
        return 50
    else:
        return 30


def _compute_score(criteria_passed, rs_rating, pct_from_high, stock_return_1y):
    """Composite score matching the JS dashboard formula."""
    return round(
        (criteria_passed / 8) * 40
        + (rs_rating / 100) * 35
        + max((25 + pct_from_high) / 25 * 15, 0)
        + min(stock_return_1y / 200, 1) * 10
    )


def _compute_status(close, high, ma50_series, vol_series, criteria_passed, pct_from_high):
    """
    Determine status for a ticker.
    Returns one of: CLIMACTIC_SELL, EXIT_STRONG, EXIT_WEAK, EXTENDED, ENTRY, HOLD
    """
    if len(close) < 20:
        return "HOLD"

    current_price = float(close.iloc[-1])
    ma50_current = float(ma50_series.iloc[-1]) if not ma50_series.isna().iloc[-1] else None

    if ma50_current is None:
        return "HOLD"

    pct_above_ma50 = (current_price / ma50_current - 1) * 100

    # Volume-related checks
    avg_vol_20 = float(vol_series.iloc[-20:].mean()) if len(vol_series) >= 20 else None

    # Check climactic action: 2+ wide-range up days on heavy volume in last 3 days AND >25% above MA50
    if pct_above_ma50 > 25 and avg_vol_20 is not None:
        recent_days = min(3, len(close))
        climactic_count = 0
        for i in range(-recent_days, 0):
            day_return = (float(close.iloc[i]) / float(close.iloc[i - 1]) - 1) * 100
            day_vol = float(vol_series.iloc[i])
            if day_return > 2.0 and day_vol > avg_vol_20 * 1.5:
                climactic_count += 1
        if climactic_count >= 2:
            return "CLIMACTIC_SELL"

    # EXTENDED: >25% above MA50 (no climactic action)
    if pct_above_ma50 > 25:
        return "EXTENDED"

    # Check MA50 crossunder in last 3 bars
    if len(close) >= 4 and len(ma50_series) >= 4:
        # Was price above MA50 3 bars ago but now below?
        crossed_below = False
        for lookback in range(1, 4):
            prev_close = float(close.iloc[-lookback - 1])
            prev_ma50 = float(ma50_series.iloc[-lookback - 1])
            curr_close = float(close.iloc[-lookback])
            curr_ma50 = float(ma50_series.iloc[-lookback])
            if not pd.isna(prev_ma50) and not pd.isna(curr_ma50):
                if prev_close > prev_ma50 and curr_close < curr_ma50:
                    crossed_below = True
                    break

        if crossed_below:
            if avg_vol_20 is not None:
                recent_vol = float(vol_series.iloc[-1])
                if recent_vol > avg_vol_20 * 1.5:
                    return "EXIT_STRONG"
            return "EXIT_WEAK"

    # ENTRY: criteria_passed >= 7
    if criteria_passed >= 7:
        return "ENTRY"

    return "HOLD"


def _process_ticker(entry, spy_return_1y):
    """Download and process a single watchlist ticker. Returns result dict."""
    yf_ticker = entry["yf"]
    try:
        raw = yf.download(
            yf_ticker, period="2y",
            auto_adjust=True, progress=False
        )
        if raw is None or raw.empty:
            return _no_data_entry(entry)

        # Flatten MultiIndex columns if present
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = raw.columns.get_level_values(0)

        raw = raw.dropna(how="all")

        if len(raw) < MIN_BARS:
            return _no_data_entry(entry)

        close = raw["Close"].squeeze()
        high = raw["High"].squeeze()
        volume = raw["Volume"].squeeze() if "Volume" in raw.columns else pd.Series([None] * len(raw))

        n = len(close)

        # Compute moving averages (use what's available)
        ma50_series = close.rolling(50).mean()
        ma150_series = close.rolling(150).mean()
        ma200_series = close.rolling(200).mean()

        current_price = float(close.iloc[-1])
        if pd.isna(current_price) or current_price <= 0:
            return _no_data_entry(entry)
        ma50 = float(ma50_series.iloc[-1]) if n >= 50 else None
        ma150 = float(ma150_series.iloc[-1]) if n >= 150 else None
        ma200 = float(ma200_series.iloc[-1]) if n >= 200 else None

        # 1-month and 4-month ago MA200 (for trend)
        ma200_1m = float(ma200_series.iloc[-22]) if n >= 222 and not pd.isna(ma200_series.iloc[-22]) else None
        ma200_4m = float(ma200_series.iloc[-88]) if n >= 288 and not pd.isna(ma200_series.iloc[-88]) else None

        week_52_high = float(high.iloc[-252:].max()) if n >= 252 else float(high.max())
        pct_from_high = round((current_price / week_52_high - 1) * 100, 1)

        # 1-year return: use up to 252 bars back
        start_close = float(close.iloc[-252]) if n >= 252 else float(close.iloc[0])
        stock_return_1y = round((current_price / start_close - 1) * 100, 1)

        rs_rating = _compute_rs_rating(stock_return_1y, spy_return_1y)

        # Minervini criteria
        c1 = (current_price > ma50) if ma50 is not None else False
        c2 = (current_price > ma150) if ma150 is not None else False
        c3 = (current_price > ma200) if ma200 is not None else False
        c4 = (ma50 > ma150) if (ma50 is not None and ma150 is not None) else False
        c5 = (ma150 > ma200) if (ma150 is not None and ma200 is not None) else False
        c6 = (ma200 > ma200_1m and ma200 > ma200_4m) if (ma200 is not None and ma200_1m is not None and ma200_4m is not None) else False
        c7 = (current_price >= week_52_high * 0.75)
        c8 = (rs_rating >= 70)

        criteria_passed = sum([c1, c2, c3, c4, c5, c6, c7, c8])

        score = _compute_score(criteria_passed, rs_rating, pct_from_high, stock_return_1y)

        status = _compute_status(
            close, high,
            ma50_series,
            volume,
            criteria_passed,
            pct_from_high
        )

        return {
            "display": entry["display"],
            "yf_ticker": yf_ticker,
            "name": entry["name"],
            "status": status,
            "price": round(current_price, 4),
            "ma50": round(ma50, 4) if ma50 is not None else 0.0,
            "ma200": round(ma200, 4) if ma200 is not None else 0.0,
            "criteria_passed": criteria_passed,
            "rs_rating": rs_rating,
            "pct_from_high": pct_from_high,
            "stock_return_1y": stock_return_1y,
            "score": score,
        }

    except Exception as e:
        print(f"  ⚠️  {entry['display']} ({yf_ticker}) failed: {e}")
        return _no_data_entry(entry)


def run_watchlist_screen(spy_data=None):
    """
    Main entry point. Downloads and processes all watchlist tickers.

    Args:
        spy_data: Optional pre-fetched SPY DataFrame (avoids re-download).

    Returns:
        List of dicts, one per ticker, in WATCHLIST order.
    """
    # Get SPY 1-year return for RS calculation
    try:
        if spy_data is None or spy_data.empty:
            print("  Downloading SPY for watchlist RS calculation...")
            spy_data = yf.download("SPY", period="1y", auto_adjust=True, progress=False)

        spy_close = spy_data["Close"].squeeze()
        spy_return_1y = float((spy_close.iloc[-1] / spy_close.iloc[0] - 1) * 100)
        print(f"  SPY 1Y return: {spy_return_1y:.1f}%")
    except Exception as e:
        print(f"  ⚠️  Could not compute SPY return ({e}), using 0")
        spy_return_1y = 0.0

    results = []
    for entry in WATCHLIST:
        print(f"  Processing {entry['display']} ({entry['yf']})...")
        result = _process_ticker(entry, spy_return_1y)
        results.append(result)

    return results


if __name__ == "__main__":
    import json
    print("Running watchlist screen...")
    r = run_watchlist_screen()
    print(json.dumps(r, indent=2))
