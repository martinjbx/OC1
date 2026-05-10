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

def _batch_download(tickers, period='1y', batch_size=200):
    """
    Download price data for many tickers using yf.download() in batches.
    Returns dict: {ticker -> DataFrame} for tickers with sufficient data.
    """
    import time
    all_data = {}
    batches = [tickers[i:i+batch_size] for i in range(0, len(tickers), batch_size)]
    print(f"  Downloading {len(tickers)} tickers in {len(batches)} batches of {batch_size}...")

    for b_idx, batch in enumerate(batches, 1):
        for attempt in range(3):
            try:
                raw = yf.download(
                    batch, period=period,
                    group_by='ticker', auto_adjust=True,
                    progress=False, threads=True
                )
                break
            except Exception as e:
                print(f"  Batch {b_idx} attempt {attempt+1} failed: {e}")
                time.sleep(10)
        else:
            print(f"  Batch {b_idx} skipped after 3 failures")
            continue

        # Parse multi-ticker response
        if len(batch) == 1:
            # Single ticker: flat DataFrame
            ticker = batch[0]
            if not raw.empty and len(raw) >= 200:
                all_data[ticker] = raw
        else:
            for ticker in batch:
                try:
                    df = raw[ticker].dropna(how='all')
                    if not df.empty and len(df) >= 200:
                        all_data[ticker] = df
                except (KeyError, TypeError):
                    pass

        if b_idx % 5 == 0:
            print(f"  Batch {b_idx}/{len(batches)} done — {len(all_data)} valid so far")
        time.sleep(1)  # brief pause between batches

    return all_data


def run_minervini_json():
    """Run Minervini screener and return JSON"""
    import time
    print("Running Minervini screener...")

    # Load tickers
    ticker_file = Path(__file__).parent / "tickers.csv"
    tickers_df = pd.read_csv(ticker_file, encoding='utf-8-sig')
    tickers = tickers_df['Symbol'].dropna().tolist()
    print(f"Loaded {len(tickers)} tickers")

    # Download SPY benchmark
    print("Downloading SPY benchmark...")
    spy_data = None
    for attempt in range(5):
        try:
            spy_data = yf.download('SPY', period='1y', auto_adjust=True, progress=False)
            if len(spy_data) > 0:
                break
        except Exception as e:
            print(f"SPY attempt {attempt+1} failed: {e}, retrying in 30s...")
            time.sleep(30)
    if spy_data is None or len(spy_data) == 0:
        raise Exception("Could not fetch SPY benchmark data after 5 attempts")

    # Batch-download all tickers (much less rate-limited than individual requests)
    print("Batch downloading price data...")
    stock_data_map = _batch_download(tickers, period='1y', batch_size=200)
    print(f"  {len(stock_data_map)} / {len(tickers)} tickers with valid data (≥200 days)")

    # Apply Minervini criteria to each stock with valid data
    print("Applying Minervini criteria...")
    results = []
    spy_return = float((spy_data['Close'].iloc[-1] / spy_data['Close'].iloc[0] - 1) * 100)

    for ticker, data in stock_data_map.items():
        try:
            data = data.copy()
            data['MA_50']  = data['Close'].rolling(50).mean()
            data['MA_150'] = data['Close'].rolling(150).mean()
            data['MA_200'] = data['Close'].rolling(200).mean()

            current_price = float(data['Close'].iloc[-1])
            ma_50  = float(data['MA_50'].iloc[-1])
            ma_150 = float(data['MA_150'].iloc[-1])
            ma_200 = float(data['MA_200'].iloc[-1])
            ma_200_1m  = float(data['MA_200'].iloc[-22]) if len(data) >= 22 else ma_200
            ma_200_4m  = float(data['MA_200'].iloc[-88]) if len(data) >= 88 else ma_200
            week_52_high = float(data['High'].max())
            stock_return = float((data['Close'].iloc[-1] / data['Close'].iloc[0] - 1) * 100)

            # RS rating
            rel = stock_return - spy_return
            rs = 95 if rel > 50 else 85 if rel > 30 else 75 if rel > 15 else 65 if rel > 0 else 50 if rel > -15 else 30

            criteria = {
                '1': current_price > ma_50,
                '2': current_price > ma_150,
                '3': current_price > ma_200,
                '4': ma_50 > ma_150,
                '5': ma_150 > ma_200,
                '6': ma_200 > ma_200_1m and ma_200 > ma_200_4m,
                '7': current_price >= week_52_high * 0.75,
                '8': rs >= 70,
            }
            passed = sum(criteria.values())

            results.append({
                'ticker': ticker,
                'price': round(current_price, 2),
                'ma_50': round(ma_50, 2),
                'ma_150': round(ma_150, 2),
                'ma_200': round(ma_200, 2),
                '52w_high': round(week_52_high, 2),
                'pct_from_high': round((current_price / week_52_high - 1) * 100, 1),
                'rs_rating': rs,
                'stock_return_1y': round(stock_return, 1),
                'criteria_passed': passed,
                'all_criteria_met': passed == 8,
            })
        except Exception:
            pass

    # Extract 7+ candidates
    candidates = [
        {
            'ticker': str(s['ticker']),
            'price': float(s['price']),
            'pct_from_high': float(s['pct_from_high']),
            'rs_rating': int(s['rs_rating']),
            'stock_return_1y': float(s['stock_return_1y']),
            'criteria_passed': int(s['criteria_passed']),
            'all_criteria_met': bool(s['all_criteria_met']),
        }
        for s in results if s['criteria_passed'] >= 7
    ]

    # Deduplicate
    seen = {}
    for c in candidates:
        t = c['ticker']
        if t not in seen or c['criteria_passed'] > seen[t]['criteria_passed'] or \
           (c['criteria_passed'] == seen[t]['criteria_passed'] and c['rs_rating'] > seen[t]['rs_rating']):
            seen[t] = c
    candidates = list(seen.values())
    candidates.sort(key=lambda x: (x['rs_rating'], -x['pct_from_high']), reverse=True)

    return {
        'scan_date': datetime.utcnow().isoformat(),
        'total_attempted': len(tickers),
        'total_scanned': len(results),       # tickers with ≥200 days valid data
        'candidates_7_plus': len(candidates),
        'candidates_all_8': len([c for c in candidates if c['all_criteria_met']]),
        'top_candidates': candidates[:50],
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
