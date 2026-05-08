"""
Structure Break + SMMA 15/29 Screener
Rule-based system with zero ambiguity

Entry Rules (LONG):
1. Bullish structure break confirmed (close above most recent lower high)
2. SMMA 15 crosses above SMMA 29
3. Both SMAs sloping upward
4. RSI(20) > 50 AND was below 50 within last 10 candles
5. Filters: SMAs not flat, price not in range midpoint
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

from fetch_data import fetch_historical_data
from tickers import get_all_unique_tickers
from indicators import smma, rsi


def identify_swing_highs(df: pd.DataFrame, lookback: int = 2) -> pd.Series:
    """
    Identify swing highs: a high with at least 'lookback' lower highs on both sides
    
    Args:
        df: DataFrame with 'high' column
        lookback: Number of bars to check on each side (default 2)
    
    Returns:
        Boolean series marking swing highs
    """
    highs = df['high'].values
    is_swing = np.zeros(len(highs), dtype=bool)
    
    for i in range(lookback, len(highs) - lookback):
        current = highs[i]
        
        # Check left side
        left_ok = all(current > highs[i-j] for j in range(1, lookback + 1))
        
        # Check right side
        right_ok = all(current > highs[i+j] for j in range(1, lookback + 1))
        
        if left_ok and right_ok:
            is_swing[i] = True
    
    return pd.Series(is_swing, index=df.index)


def identify_swing_lows(df: pd.DataFrame, lookback: int = 2) -> pd.Series:
    """
    Identify swing lows: a low with at least 'lookback' higher lows on both sides
    
    Args:
        df: DataFrame with 'low' column
        lookback: Number of bars to check on each side (default 2)
    
    Returns:
        Boolean series marking swing lows
    """
    lows = df['low'].values
    is_swing = np.zeros(len(lows), dtype=bool)
    
    for i in range(lookback, len(lows) - lookback):
        current = lows[i]
        
        # Check left side
        left_ok = all(current < lows[i-j] for j in range(1, lookback + 1))
        
        # Check right side
        right_ok = all(current < lows[i+j] for j in range(1, lookback + 1))
        
        if left_ok and right_ok:
            is_swing[i] = True
    
    return pd.Series(is_swing, index=df.index)


def detect_bullish_structure_break(df: pd.DataFrame, lookback: int = 50) -> Dict:
    """
    Detect bullish structure break:
    - Find most recent swing low (L1)
    - Find most recent lower high (H1) after L1
    - Check if price closed above H1
    
    Args:
        df: DataFrame with OHLC data
        lookback: How far back to look for structure (default 50 bars)
    
    Returns:
        dict with structure break info
    """
    recent = df.tail(lookback).copy()
    
    # Identify swing points
    recent['swing_high'] = identify_swing_highs(recent)
    recent['swing_low'] = identify_swing_lows(recent)
    
    # Get swing highs and lows
    swing_highs = recent[recent['swing_high'] == True]
    swing_lows = recent[recent['swing_low'] == True]
    
    if len(swing_lows) == 0 or len(swing_highs) == 0:
        return {
            'has_break': False,
            'reason': 'Insufficient swing points'
        }
    
    # Find most recent swing low
    L1_idx = swing_lows.index[-1]
    L1_price = recent.loc[L1_idx, 'low']
    
    # Find swing highs after L1
    highs_after_L1 = swing_highs[swing_highs.index > L1_idx]
    
    if len(highs_after_L1) == 0:
        return {
            'has_break': False,
            'reason': 'No swing high after most recent swing low'
        }
    
    # Check if we're in downtrend structure (lower highs)
    # Find most recent "lower high" (H1)
    # For simplicity, take the most recent swing high after L1
    H1_idx = highs_after_L1.index[-1]
    H1_price = recent.loc[H1_idx, 'high']
    
    # Current close
    current_close = recent['close'].iloc[-1]
    current_idx = recent.index[-1]
    
    # Check if close is above H1
    closed_above_H1 = current_close > H1_price
    
    # Check if this happened recently (within last 5 bars)
    bars_since_H1 = len(recent[recent.index > H1_idx])
    is_recent = bars_since_H1 <= 10
    
    return {
        'has_break': closed_above_H1 and is_recent,
        'L1_price': float(L1_price),
        'H1_price': float(H1_price),
        'current_close': float(current_close),
        'closed_above_H1': closed_above_H1,
        'bars_since_structure': bars_since_H1,
        'is_recent': is_recent,
        'reason': None if (closed_above_H1 and is_recent) else 'No recent break above H1'
    }


def check_smma_slope(df: pd.DataFrame, column: str, lookback: int = 3, threshold: float = 0.001) -> bool:
    """
    Check if SMMA is sloping upward
    
    Args:
        df: DataFrame with SMMA column
        column: Column name to check
        lookback: Bars to look back
        threshold: Minimum percentage change (0.001 = 0.1%)
    
    Returns:
        True if sloping upward
    """
    recent = df[column].tail(lookback + 1)
    if len(recent) < 2:
        return False
    
    current = recent.iloc[-1]
    past = recent.iloc[0]
    
    if pd.isna(current) or pd.isna(past) or past == 0:
        return False
    
    pct_change = (current - past) / past
    return pct_change > threshold


def check_smma_flat(df: pd.DataFrame, column: str, lookback: int = 5, threshold: float = 0.001) -> bool:
    """
    Check if SMMA is flat (not trending)
    
    Args:
        df: DataFrame with SMMA column
        column: Column name to check
        lookback: Bars to check
        threshold: Maximum percentage change to be considered flat (0.001 = 0.1%)
    
    Returns:
        True if flat
    """
    recent = df[column].tail(lookback + 1)
    if len(recent) < 2:
        return True
    
    current = recent.iloc[-1]
    past = recent.iloc[0]
    
    if pd.isna(current) or pd.isna(past) or past == 0:
        return True
    
    pct_change = abs((current - past) / past)
    return pct_change < threshold


def check_in_range_midpoint(df: pd.DataFrame, lookback: int = 20) -> bool:
    """
    Check if current price is near the midpoint of recent range
    (filter out choppy, range-bound conditions)
    
    Args:
        df: DataFrame with close prices
        lookback: Period to calculate range
    
    Returns:
        True if in midpoint (bad), False if near edges (good)
    """
    recent = df['close'].tail(lookback)
    if len(recent) < lookback:
        return True
    
    range_high = recent.max()
    range_low = recent.min()
    range_mid = (range_high + range_low) / 2
    current = recent.iloc[-1]
    
    # Check if within 20% of midpoint
    range_size = range_high - range_low
    if range_size == 0:
        return True
    
    distance_from_mid = abs(current - range_mid)
    threshold = 0.2 * range_size
    
    return distance_from_mid < threshold


def check_rsi_shift(df: pd.DataFrame, lookback: int = 10) -> Dict:
    """
    Check if RSI shifted from below 50 to above 50 within lookback period
    
    Args:
        df: DataFrame with 'rsi' column
        lookback: Bars to look back
    
    Returns:
        dict with RSI shift info
    """
    recent = df['rsi'].tail(lookback + 1)
    current_rsi = recent.iloc[-1]
    
    if pd.isna(current_rsi):
        return {
            'meets_condition': False,
            'current_rsi': None,
            'was_below_50': False,
            'reason': 'RSI is NaN'
        }
    
    # Check if current RSI > 50
    above_50_now = current_rsi > 50
    
    # Check if RSI was below 50 within lookback
    was_below_50 = any(recent.iloc[:-1] < 50)
    
    # Check if there was a clear shift (was below 50, now above)
    meets_condition = above_50_now and was_below_50
    
    return {
        'meets_condition': meets_condition,
        'current_rsi': float(current_rsi),
        'above_50_now': above_50_now,
        'was_below_50': was_below_50,
        'min_rsi': float(recent.min()),
        'reason': None if meets_condition else f"Above50:{above_50_now} WasBelow:{was_below_50}"
    }


def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate all required indicators for the strategy
    
    Args:
        df: DataFrame with OHLC data
    
    Returns:
        DataFrame with added indicators
    """
    df = df.copy()
    
    # Calculate SMAs
    df['smma_15'] = smma(df['close'], 15)
    df['smma_29'] = smma(df['close'], 29)
    
    # Calculate RSI
    df['rsi'] = rsi(df['close'], 20)
    
    # Detect SMMA crossover
    df['smma_cross'] = np.where(df['smma_15'] > df['smma_29'], 1, -1)
    df['smma_signal'] = df['smma_cross'].diff()
    
    return df


def screen_ticker_for_structure_entry(ticker: str) -> Optional[Dict]:
    """
    Screen a single ticker for structure break + SMMA entry
    
    Args:
        ticker: Stock symbol
    
    Returns:
        dict with screening results or None
    """
    # Fetch data (need enough for structure detection)
    df = fetch_historical_data(ticker, period="6mo")
    
    if df is None or len(df) < 100:
        return None
    
    # Calculate indicators
    df = calculate_indicators(df)
    
    # Check 1: Bullish structure break
    structure = detect_bullish_structure_break(df, lookback=50)
    if not structure['has_break']:
        return None
    
    # Check 2: SMMA 15 crossed above SMMA 29 recently (within last 5 bars)
    recent_signals = df['smma_signal'].tail(5)
    has_bullish_cross = any(recent_signals == 2)
    
    if not has_bullish_cross:
        return None
    
    # Check 3: Both SMAs sloping upward
    smma_15_up = check_smma_slope(df, 'smma_15', lookback=3, threshold=0.001)
    smma_29_up = check_smma_slope(df, 'smma_29', lookback=3, threshold=0.001)
    
    if not (smma_15_up and smma_29_up):
        return None
    
    # Check 4: RSI shift (was below 50, now above)
    rsi_check = check_rsi_shift(df, lookback=10)
    if not rsi_check['meets_condition']:
        return None
    
    # Filter 1: SMAs not flat
    smma_15_flat = check_smma_flat(df, 'smma_15', lookback=5, threshold=0.001)
    smma_29_flat = check_smma_flat(df, 'smma_29', lookback=5, threshold=0.001)
    
    if smma_15_flat or smma_29_flat:
        return None
    
    # Filter 2: Not in range midpoint
    in_midpoint = check_in_range_midpoint(df, lookback=20)
    if in_midpoint:
        return None
    
    # All checks passed - generate signal
    last_row = df.iloc[-1]
    
    result = {
        'ticker': ticker,
        'date': df.index[-1].strftime('%Y-%m-%d'),
        'price': float(last_row['close']),
        'smma_15': float(last_row['smma_15']),
        'smma_29': float(last_row['smma_29']),
        'rsi': float(last_row['rsi']),
        'structure': {
            'L1_price': structure['L1_price'],
            'H1_price': structure['H1_price'],
            'current_close': structure['current_close']
        },
        'stop_loss_suggestion': structure['L1_price'],  # Stop below most recent swing low
        'signal_type': 'BUY'
    }
    
    return result


def run_structure_screen(max_tickers: Optional[int] = None, verbose: bool = True) -> Dict[str, List]:
    """
    Run structure break screener across all tickers
    
    Args:
        max_tickers: Limit number of tickers (for testing)
        verbose: Print progress
    
    Returns:
        dict with 'signals' list and stats
    """
    if verbose:
        print(f"Starting Structure Break Screener at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
    
    # Get all tickers
    tickers = get_all_unique_tickers()
    
    if not tickers:
        print("Error: No tickers loaded")
        return {'signals': [], 'errors': 0, 'total_screened': 0}
    
    if max_tickers:
        tickers = tickers[:max_tickers]
    
    if verbose:
        print(f"Screening {len(tickers)} tickers...")
        print(f"Strategy: Structure Break + SMMA 15/29 + RSI Shift")
        print("=" * 60)
    
    signals = []
    errors = 0
    
    for i, ticker in enumerate(tickers, 1):
        if verbose and i % 50 == 0:
            print(f"Progress: {i}/{len(tickers)} ({100*i//len(tickers)}%) - Signals found: {len(signals)}")
        
        try:
            result = screen_ticker_for_structure_entry(ticker)
            
            if result:
                signals.append(result)
                if verbose:
                    print(f"✅ {ticker}: ${result['price']:.2f} | RSI: {result['rsi']:.1f} | SL: ${result['stop_loss_suggestion']:.2f}")
        
        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"❌ Error screening {ticker}: {e}")
    
    if verbose:
        print("\n" + "=" * 60)
        print(f"✅ Screener complete!")
        print(f"Signals found: {len(signals)}")
        print(f"Total screened: {len(tickers)}")
        print(f"Errors: {errors}")
        print("=" * 60)
    
    return {
        'signals': signals,
        'total_screened': len(tickers),
        'errors': errors,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }


def format_structure_report(results: Dict) -> str:
    """
    Format screening results as text report
    
    Args:
        results: Dict from run_structure_screen
    
    Returns:
        Formatted report string
    """
    lines = []
    lines.append("=" * 70)
    lines.append("📊 STRUCTURE BREAK + SMMA 15/29 SCREENER REPORT")
    lines.append(f"Generated: {results['timestamp']}")
    lines.append("=" * 70)
    lines.append("")
    lines.append("Strategy Rules:")
    lines.append("  ✓ Bullish structure break (close above recent lower high)")
    lines.append("  ✓ SMMA 15 crosses above SMMA 29")
    lines.append("  ✓ Both SMAs trending upward")
    lines.append("  ✓ RSI shifted from below 50 to above 50")
    lines.append("  ✓ SMAs not flat")
    lines.append("  ✓ Price not in range midpoint")
    lines.append("=" * 70)
    
    signals = results['signals']
    
    if signals:
        lines.append(f"\n🟢 SIGNALS FOUND: {len(signals)}")
        lines.append("-" * 70)
        lines.append(f"{'Ticker':<8} {'Price':>8} {'SMMA15':>8} {'SMMA29':>8} {'RSI':>6} {'SL':>8}")
        lines.append("-" * 70)
        
        for signal in signals:
            lines.append(
                f"{signal['ticker']:<8} "
                f"${signal['price']:>7.2f} "
                f"${signal['smma_15']:>7.2f} "
                f"${signal['smma_29']:>7.2f} "
                f"{signal['rsi']:>6.1f} "
                f"${signal['stop_loss_suggestion']:>7.2f}"
            )
        
        lines.append("-" * 70)
        lines.append("\nStructure Details:")
        lines.append("-" * 70)
        
        for signal in signals:
            lines.append(f"\n{signal['ticker']}:")
            lines.append(f"  Current: ${signal['structure']['current_close']:.2f}")
            lines.append(f"  H1 (broken): ${signal['structure']['H1_price']:.2f}")
            lines.append(f"  L1 (swing low): ${signal['structure']['L1_price']:.2f}")
            lines.append(f"  Stop Loss: ${signal['stop_loss_suggestion']:.2f}")
    else:
        lines.append("\n🟢 SIGNALS FOUND: 0")
        lines.append("No setups meeting all criteria today.")
    
    lines.append("\n" + "=" * 70)
    lines.append(f"Total Tickers Screened: {results['total_screened']}")
    if results['errors'] > 0:
        lines.append(f"Errors: {results['errors']}")
    lines.append("=" * 70)
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test with limited tickers
    print("Testing structure screener (first 50 tickers)...")
    results = run_structure_screen(max_tickers=50, verbose=True)
    
    print("\n" + format_structure_report(results))
