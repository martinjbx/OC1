#!/usr/bin/env python3
"""
Daily screener runner that outputs JSON for dashboard
No AI tokens - pure Python cron job
"""

import sys
import json
from pathlib import Path
from datetime import datetime
import pandas as pd
import yfinance as yf
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add src and parent to path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from structure_screener import run_structure_screen
from minervini_sepa_screener import scan_ticker as minervini_scan_ticker
from exit_checker import run_exit_check

def run_structure_json():
    """Run structure screener and return JSON"""
    print("Running structure screener...")
    results = run_structure_screen(max_tickers=None, verbose=False)
    
    signals = []
    for signal in results['signals']:
        signals.append({
            'ticker': str(signal.get('ticker', '')),
            'price': float(signal.get('price', 0)),
            'smma15': float(signal.get('smma_15', signal.get('smma15', 0))),
            'smma29': float(signal.get('smma_29', signal.get('smma29', 0))),
            'rsi': float(signal.get('rsi', 0)),
            'volume_surge': bool(signal.get('volume_surge', False))
        })
    
    return {
        'scan_date': datetime.utcnow().isoformat(),
        'total_scanned': results.get('total_screened', 0),
        'signals_found': len(signals),
        'signals': signals
    }

def run_minervini_json():
    """Run Minervini screener and return JSON"""
    print("Running Minervini screener...")
    
    # Load tickers
    ticker_file = Path(__file__).parent / "tickers.csv"
    tickers_df = pd.read_csv(ticker_file, encoding='utf-8-sig')
    tickers = tickers_df['Symbol'].dropna().tolist()
    
    print(f"Loaded {len(tickers)} tickers")
    
    # Download S&P 500 benchmark data (with retry on rate limit)
    print("Downloading SPY benchmark...")
    spy_data = None
    for attempt in range(5):
        try:
            spy = yf.Ticker('SPY')
            spy_data = spy.history(period='1y')
            if len(spy_data) > 0:
                break
        except Exception as e:
            print(f"SPY attempt {attempt+1} failed: {e}, retrying in 30s...")
            import time; time.sleep(30)
    if spy_data is None or len(spy_data) == 0:
        raise Exception("Could not fetch SPY benchmark data after 5 attempts")
    
    # Scan in parallel
    print("Scanning tickers...")
    results = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(minervini_scan_ticker, ticker, spy_data, False): ticker 
                  for ticker in tickers}
        
        for i, future in enumerate(as_completed(futures), 1):
            ticker = futures[future]
            try:
                _, passes, criteria, stock_data = future.result()
                
                if stock_data:
                    results.append(stock_data)
                    
                if i % 50 == 0:
                    print(f"Progress: {i}/{len(tickers)}")
                    
            except Exception as e:
                # Silently skip errors
                pass
    
    # Extract candidates (convert numpy types to Python types)
    candidates = []
    for stock in results:
        if stock['criteria_passed'] >= 7:
            candidates.append({
                'ticker': str(stock['ticker']),
                'price': float(stock['price']),
                'pct_from_high': float(stock['pct_from_high']),
                'rs_rating': int(stock['rs_rating']),
                'stock_return_1y': float(stock['stock_return_1y']),
                'criteria_passed': int(stock['criteria_passed']),
                'all_criteria_met': bool(stock['all_criteria_met'])
            })
    
    # Deduplicate by ticker (keep highest criteria_passed, then highest RS)
    seen = {}
    for c in candidates:
        ticker = c['ticker']
        if ticker not in seen or c['criteria_passed'] > seen[ticker]['criteria_passed'] or \
           (c['criteria_passed'] == seen[ticker]['criteria_passed'] and c['rs_rating'] > seen[ticker]['rs_rating']):
            seen[ticker] = c
    candidates = list(seen.values())

    # Sort by RS rating, then proximity to high
    candidates.sort(key=lambda x: (x['rs_rating'], -x['pct_from_high']), reverse=True)
    
    return {
        'scan_date': datetime.utcnow().isoformat(),
        'total_scanned': len(results),
        'candidates_7_plus': len(candidates),
        'candidates_all_8': len([c for c in candidates if c['all_criteria_met']]),
        'top_candidates': candidates[:50]  # Top 50
    }

def main():
    output_dir = Path(__file__).parent / "dashboard" / "data"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Run structure screener
    try:
        structure_data = run_structure_json()
        structure_file = output_dir / "structure_latest.json"
        with open(structure_file, 'w') as f:
            json.dump(structure_data, f, indent=2)
        print(f"✅ Structure results: {structure_file}")
    except Exception as e:
        print(f"❌ Structure screener failed: {e}")
        structure_data = {
            'scan_date': datetime.utcnow().isoformat(),
            'total_scanned': 0,
            'signals_found': 0,
            'signals': []
        }
    
    # Brief pause between screeners to avoid rate limits
    import time
    print("Pausing 60s between screeners to avoid rate limits...")
    time.sleep(60)

    # Run Minervini screener
    minervini_file = output_dir / "minervini_latest.json"
    try:
        minervini_data = run_minervini_json()
        with open(minervini_file, 'w') as f:
            json.dump(minervini_data, f, indent=2)
        print(f"✅ Minervini results: {minervini_file}")
    except Exception as e:
        print(f"❌ Minervini screener failed: {e}")
        # Fall back to the previous run's data if available, so summary stays accurate
        if minervini_file.exists():
            print("  ↳ Using previous Minervini results for summary")
            with open(minervini_file) as f:
                minervini_data = json.load(f)
        else:
            minervini_data = {
                'scan_date': datetime.utcnow().isoformat(),
                'total_scanned': 0,
                'candidates_7_plus': 0,
                'candidates_all_8': 0,
                'top_candidates': []
            }
    
    # Run exit checker (uses today's Minervini candidates to update watchlist)
    print("\nRunning exit signal checker...")
    exit_data = None
    try:
        minervini_candidates = minervini_data.get('top_candidates', [])
        exit_data = run_exit_check(candidates=minervini_candidates)
        exit_file = output_dir / "exit_alerts.json"
        with open(exit_file, 'w') as f:
            json.dump(exit_data, f, indent=2)
        print(f"✅ Exit alerts: {len(exit_data.get('strong_exits', []))} strong, "
              f"{len(exit_data.get('weak_exits', []))} weak — {exit_file}")
    except Exception as e:
        print(f"❌ Exit checker failed: {e}")
        exit_data = None

    # Create combined summary
    summary = {
        'last_update': datetime.utcnow().isoformat(),
        'structure': {
            'signals': structure_data['signals_found'],
            'scanned': structure_data['total_scanned']
        },
        'minervini': {
            'candidates_7_plus': minervini_data['candidates_7_plus'],
            'candidates_all_8': minervini_data['candidates_all_8'],
            'scanned': minervini_data['total_scanned']
        },
        'exits': {
            'strong': len(exit_data.get('strong_exits', [])) if exit_data else 0,
            'weak': len(exit_data.get('weak_exits', [])) if exit_data else 0,
            'climactic_sells': len(exit_data.get('climactic_sells', [])) if exit_data else 0,
            'partial_profits': len(exit_data.get('partial_profits', [])) if exit_data else 0,
            'watchlist_size': exit_data.get('watchlist_size', 0) if exit_data else 0,
        }
    }
    
    summary_file = output_dir / "summary.json"
    with open(summary_file, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"✅ Summary: {summary_file}")
    
    print("\n🎉 All screeners complete!")

if __name__ == "__main__":
    main()
