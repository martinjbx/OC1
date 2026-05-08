#!/usr/bin/env python3
"""
Structure Break Screener - Diagnostic Version
Shows how many tickers pass each filter stage
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fetch_data import fetch_historical_data
from tickers import get_all_unique_tickers
from structure_screener import (
    calculate_indicators,
    detect_bullish_structure_break,
    check_smma_slope,
    check_smma_flat,
    check_in_range_midpoint,
    check_rsi_shift
)

def diagnostic_screen(max_tickers=None):
    """Run diagnostic screen showing filter funnel"""
    
    print("=" * 70)
    print("STRUCTURE BREAK SCREENER - DIAGNOSTIC MODE")
    print("=" * 70)
    
    tickers = get_all_unique_tickers()
    if max_tickers:
        tickers = tickers[:max_tickers]
    
    print(f"Screening {len(tickers)} tickers...\n")
    
    # Track how many pass each stage
    stats = {
        'total': 0,
        'sufficient_data': 0,
        'structure_break': 0,
        'smma_cross': 0,
        'smma_slope': 0,
        'rsi_shift': 0,
        'not_flat': 0,
        'not_midpoint': 0,
        'final_signals': 0
    }
    
    signals = []
    
    for i, ticker in enumerate(tickers, 1):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(tickers)}")
        
        try:
            stats['total'] += 1
            
            # Fetch data
            df = fetch_historical_data(ticker, period="6mo")
            if df is None or len(df) < 100:
                continue
            
            stats['sufficient_data'] += 1
            
            # Calculate indicators
            df = calculate_indicators(df)
            
            # Check 1: Structure break
            structure = detect_bullish_structure_break(df, lookback=50)
            if not structure['has_break']:
                continue
            stats['structure_break'] += 1
            
            # Check 2: SMMA cross
            recent_signals = df['smma_signal'].tail(5)
            has_bullish_cross = any(recent_signals == 2)
            if not has_bullish_cross:
                continue
            stats['smma_cross'] += 1
            
            # Check 3: SMMA slope
            smma_15_up = check_smma_slope(df, 'smma_15', lookback=3, threshold=0.001)
            smma_29_up = check_smma_slope(df, 'smma_29', lookback=3, threshold=0.001)
            if not (smma_15_up and smma_29_up):
                continue
            stats['smma_slope'] += 1
            
            # Check 4: RSI shift
            rsi_check = check_rsi_shift(df, lookback=10)
            if not rsi_check['meets_condition']:
                continue
            stats['rsi_shift'] += 1
            
            # Filter 1: Not flat
            smma_15_flat = check_smma_flat(df, 'smma_15', lookback=5, threshold=0.001)
            smma_29_flat = check_smma_flat(df, 'smma_29', lookback=5, threshold=0.001)
            if smma_15_flat or smma_29_flat:
                continue
            stats['not_flat'] += 1
            
            # Filter 2: Not in midpoint
            in_midpoint = check_in_range_midpoint(df, lookback=20)
            if in_midpoint:
                continue
            stats['not_midpoint'] += 1
            
            # Passed all filters!
            stats['final_signals'] += 1
            
            last_row = df.iloc[-1]
            signals.append({
                'ticker': ticker,
                'price': float(last_row['close']),
                'smma_15': float(last_row['smma_15']),
                'smma_29': float(last_row['smma_29']),
                'rsi': float(last_row['rsi']),
                'stop_loss': structure['L1_price']
            })
            
            print(f"✅ {ticker}: ${last_row['close']:.2f}")
        
        except Exception as e:
            continue
    
    # Print funnel
    print("\n" + "=" * 70)
    print("FILTER FUNNEL ANALYSIS")
    print("=" * 70)
    print(f"{'Stage':<40} {'Count':>10} {'% of Total':>12}")
    print("-" * 70)
    
    def print_stage(name, count, total):
        pct = 100 * count / total if total > 0 else 0
        print(f"{name:<40} {count:>10} {pct:>11.1f}%")
    
    print_stage("Total tickers attempted", stats['total'], stats['total'])
    print_stage("  → Sufficient data (100+ bars)", stats['sufficient_data'], stats['total'])
    print_stage("  → Bullish structure break", stats['structure_break'], stats['total'])
    print_stage("  → SMMA 15 crossed above 29", stats['smma_cross'], stats['total'])
    print_stage("  → Both SMAs trending up", stats['smma_slope'], stats['total'])
    print_stage("  → RSI shifted <50 to >50", stats['rsi_shift'], stats['total'])
    print_stage("  → SMAs not flat", stats['not_flat'], stats['total'])
    print_stage("  → Not in range midpoint", stats['not_midpoint'], stats['total'])
    print("-" * 70)
    print_stage("✅ FINAL SIGNALS", stats['final_signals'], stats['total'])
    print("=" * 70)
    
    # Show signals
    if signals:
        print(f"\n🟢 SIGNALS ({len(signals)}):")
        print("-" * 70)
        for s in signals:
            print(f"{s['ticker']:<8} ${s['price']:>7.2f} | SMMA: {s['smma_15']:.2f}/{s['smma_29']:.2f} | RSI: {s['rsi']:.1f} | SL: ${s['stop_loss']:.2f}")
    else:
        print("\n🟢 No signals found")
    
    return stats, signals

if __name__ == "__main__":
    stats, signals = diagnostic_screen(max_tickers=None)
