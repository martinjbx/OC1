#!/usr/bin/env python3
"""
Structure Break Screener - Watchlist Mode
Shows tickers that are CLOSE to triggering (missing only 1-2 conditions)
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

def watchlist_screen(max_tickers=None):
    """Find tickers close to triggering (relaxed criteria)"""
    
    print("=" * 70)
    print("STRUCTURE BREAK WATCHLIST - NEAR-TRIGGER CANDIDATES")
    print("=" * 70)
    
    tickers = get_all_unique_tickers()
    if max_tickers:
        tickers = tickers[:max_tickers]
    
    print(f"Screening {len(tickers)} tickers...\n")
    
    # Categories
    structure_breaks = []     # Has structure break
    smma_crosses = []         # Has SMMA cross (recent)
    ready_to_cross = []       # SMMA close to crossing
    strong_rsi = []           # RSI looks good
    
    for i, ticker in enumerate(tickers, 1):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(tickers)}")
        
        try:
            df = fetch_historical_data(ticker, period="6mo")
            if df is None or len(df) < 100:
                continue
            
            df = calculate_indicators(df)
            last_row = df.iloc[-1]
            
            # Check structure break
            structure = detect_bullish_structure_break(df, lookback=50)
            
            # Check SMMA cross (within last 10 bars, relaxed)
            recent_signals = df['smma_signal'].tail(10)
            has_bullish_cross = any(recent_signals == 2)
            
            # Check if close to crossing (within 2%)
            smma_15 = last_row['smma_15']
            smma_29 = last_row['smma_29']
            if smma_15 > 0 and smma_29 > 0:
                gap = ((smma_15 - smma_29) / smma_29) * 100
                close_to_cross = -2 < gap < 2
            else:
                close_to_cross = False
            
            # Check RSI
            rsi_check = check_rsi_shift(df, lookback=15)  # Relaxed: 15 bars
            current_rsi = last_row['rsi']
            
            # Categorize
            info = {
                'ticker': ticker,
                'price': float(last_row['close']),
                'smma_15': float(smma_15),
                'smma_29': float(smma_29),
                'smma_gap': float(gap) if 'gap' in locals() else 0,
                'rsi': float(current_rsi) if not pd.isna(current_rsi) else None,
                'structure_break': structure['has_break'],
                'has_cross': has_bullish_cross,
                'close_to_cross': close_to_cross,
                'rsi_ok': rsi_check['meets_condition']
            }
            
            # Tickers with structure break
            if structure['has_break']:
                structure_breaks.append(info)
            
            # Tickers with SMMA cross
            if has_bullish_cross:
                smma_crosses.append(info)
            
            # Tickers close to SMMA cross
            if close_to_cross and smma_15 < smma_29:  # Below but close
                ready_to_cross.append(info)
            
            # Tickers with good RSI
            if rsi_check['meets_condition']:
                strong_rsi.append(info)
        
        except Exception as e:
            continue
    
    # Print results
    print("\n" + "=" * 70)
    print("📋 WATCHLIST RESULTS")
    print("=" * 70)
    
    print(f"\n🔹 BULLISH STRUCTURE BREAKS ({len(structure_breaks)})")
    print("Tickers that broke above recent lower high:")
    print("-" * 70)
    if structure_breaks:
        for t in structure_breaks[:20]:  # Top 20
            rsi_str = f"RSI:{t['rsi']:.0f}" if t['rsi'] else "RSI:N/A"
            print(f"{t['ticker']:<8} ${t['price']:>7.2f} | {rsi_str:>8} | SMMA: {t['smma_15']:.2f}/{t['smma_29']:.2f}")
    
    print(f"\n🔹 SMMA CROSSOVERS (RECENT) ({len(smma_crosses)})")
    print("Tickers where SMMA 15 crossed above 29 in last 10 days:")
    print("-" * 70)
    if smma_crosses:
        for t in smma_crosses[:20]:  # Top 20
            rsi_str = f"RSI:{t['rsi']:.0f}" if t['rsi'] else "RSI:N/A"
            print(f"{t['ticker']:<8} ${t['price']:>7.2f} | {rsi_str:>8} | SMMA: {t['smma_15']:.2f}/{t['smma_29']:.2f}")
    
    print(f"\n🔹 READY TO CROSS ({len(ready_to_cross)})")
    print("Tickers where SMMA 15 is within 2% of SMMA 29 (below):")
    print("-" * 70)
    if ready_to_cross:
        for t in ready_to_cross[:20]:  # Top 20
            rsi_str = f"RSI:{t['rsi']:.0f}" if t['rsi'] else "RSI:N/A"
            gap_str = f"{t['smma_gap']:+.1f}%"
            print(f"{t['ticker']:<8} ${t['price']:>7.2f} | {rsi_str:>8} | Gap: {gap_str:>6} | SMMA: {t['smma_15']:.2f}/{t['smma_29']:.2f}")
    
    print(f"\n🔹 RSI MOMENTUM SHIFT ({len(strong_rsi)})")
    print("Tickers with RSI shifting from <50 to >50:")
    print("-" * 70)
    if strong_rsi:
        for t in strong_rsi[:20]:  # Top 20
            rsi_str = f"RSI:{t['rsi']:.0f}" if t['rsi'] else "RSI:N/A"
            print(f"{t['ticker']:<8} ${t['price']:>7.2f} | {rsi_str:>8} | SMMA: {t['smma_15']:.2f}/{t['smma_29']:.2f}")
    
    print("\n" + "=" * 70)
    
    # Find overlaps (tickers meeting multiple criteria)
    all_tickers = set()
    ticker_scores = {}
    
    for t in structure_breaks:
        ticker = t['ticker']
        all_tickers.add(ticker)
        ticker_scores[ticker] = ticker_scores.get(ticker, 0) + 1
    
    for t in smma_crosses:
        ticker = t['ticker']
        all_tickers.add(ticker)
        ticker_scores[ticker] = ticker_scores.get(ticker, 0) + 1
    
    for t in ready_to_cross:
        ticker = t['ticker']
        all_tickers.add(ticker)
        ticker_scores[ticker] = ticker_scores.get(ticker, 0) + 1
    
    for t in strong_rsi:
        ticker = t['ticker']
        all_tickers.add(ticker)
        ticker_scores[ticker] = ticker_scores.get(ticker, 0) + 1
    
    # Find best candidates (meeting 2+ criteria)
    best_candidates = [(t, score) for t, score in ticker_scores.items() if score >= 2]
    best_candidates.sort(key=lambda x: x[1], reverse=True)
    
    print(f"\n⭐ BEST CANDIDATES (Meeting 2+ criteria): {len(best_candidates)}")
    print("-" * 70)
    if best_candidates:
        for ticker, score in best_candidates[:30]:
            # Find full info
            info = None
            for t in structure_breaks + smma_crosses + ready_to_cross + strong_rsi:
                if t['ticker'] == ticker:
                    info = t
                    break
            
            if info:
                rsi_str = f"RSI:{info['rsi']:.0f}" if info['rsi'] else "RSI:N/A"
                criteria = []
                if info['structure_break']:
                    criteria.append("Structure✓")
                if info['has_cross']:
                    criteria.append("Cross✓")
                if info['close_to_cross']:
                    criteria.append("NearCross")
                if info['rsi_ok']:
                    criteria.append("RSI✓")
                
                criteria_str = ", ".join(criteria)
                print(f"{ticker:<8} ${info['price']:>7.2f} | {rsi_str:>8} | {criteria_str}")
    
    print("=" * 70)
    
    return {
        'structure_breaks': structure_breaks,
        'smma_crosses': smma_crosses,
        'ready_to_cross': ready_to_cross,
        'strong_rsi': strong_rsi,
        'best_candidates': best_candidates
    }

if __name__ == "__main__":
    import pandas as pd
    results = watchlist_screen(max_tickers=None)
