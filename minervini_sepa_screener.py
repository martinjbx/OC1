#!/usr/bin/env python3
"""
Mark Minervini SEPA Stage 2 Screener
Implements the 8-Point Trend Template for identifying stocks in confirmed Stage 2 uptrends.

Criteria:
1. Price > 50-day MA
2. Price > 150-day MA  
3. Price > 200-day MA
4. 50-day MA > 150-day MA
5. 150-day MA > 200-day MA
6. 200-day MA trending upward (at least 1 month, preferably 4-5 months)
7. Price within 25% of 52-week high
8. Relative Strength > 70 (ideally 90+)
"""

import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')


def get_sp500_tickers():
    """Get S&P 500 ticker list"""
    url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
    try:
        tables = pd.read_html(url)
        sp500_table = tables[0]
        tickers = sp500_table['Symbol'].tolist()
        # Clean tickers (some have dots that need to be hyphens for yfinance)
        tickers = [t.replace('.', '-') for t in tickers]
        return tickers
    except Exception as e:
        print(f"Error fetching S&P 500 tickers: {e}")
        return []


def get_nasdaq100_tickers():
    """Get NASDAQ 100 ticker list"""
    url = 'https://en.wikipedia.org/wiki/Nasdaq-100'
    try:
        tables = pd.read_html(url)
        nasdaq_table = tables[4]  # The ticker table is usually the 5th table
        tickers = nasdaq_table['Ticker'].tolist()
        return tickers
    except Exception as e:
        print(f"Error fetching NASDAQ 100 tickers: {e}")
        return []


def calculate_relative_strength(ticker_data, market_data):
    """
    Calculate Relative Strength vs market (S&P 500)
    Returns a 0-100 rating based on 1-year performance percentile
    """
    try:
        # Calculate 1-year returns
        stock_return = (ticker_data['Close'].iloc[-1] / ticker_data['Close'].iloc[0] - 1) * 100
        market_return = (market_data['Close'].iloc[-1] / market_data['Close'].iloc[0] - 1) * 100
        
        # Calculate relative performance
        relative_perf = stock_return - market_return
        
        # Convert to 0-100 scale (simplified version)
        # In production, this should be ranked against all stocks
        if relative_perf > 50:
            rs_rating = 95
        elif relative_perf > 30:
            rs_rating = 85
        elif relative_perf > 15:
            rs_rating = 75
        elif relative_perf > 0:
            rs_rating = 65
        elif relative_perf > -15:
            rs_rating = 50
        else:
            rs_rating = 30
            
        return rs_rating, stock_return, market_return
    except:
        return 0, 0, 0


def check_minervini_criteria(ticker, spy_data=None, verbose=False):
    """
    Check if a stock meets all 8 Minervini SEPA Stage 2 criteria
    Returns: (passes, criteria_dict, stock_data_dict)
    """
    try:
        # Download 1 year of data (enough for 200-day MA and 52-week high)
        stock = yf.Ticker(ticker)
        data = stock.history(period='1y')
        
        if data.empty or len(data) < 200:
            return False, {}, {}
        
        # Calculate moving averages
        data['MA_50'] = data['Close'].rolling(window=50).mean()
        data['MA_150'] = data['Close'].rolling(window=150).mean()
        data['MA_200'] = data['Close'].rolling(window=200).mean()
        
        # Get current values
        current_price = data['Close'].iloc[-1]
        ma_50 = data['MA_50'].iloc[-1]
        ma_150 = data['MA_150'].iloc[-1]
        ma_200 = data['MA_200'].iloc[-1]
        
        # Calculate 52-week high
        week_52_high = data['High'].max()
        
        # Check 200-day MA trend (compare current to 1 month ago and 4 months ago)
        ma_200_1m_ago = data['MA_200'].iloc[-22] if len(data) >= 22 else ma_200
        ma_200_4m_ago = data['MA_200'].iloc[-88] if len(data) >= 88 else ma_200
        
        # Calculate Relative Strength
        rs_rating = 0
        stock_return = 0
        market_return = 0
        if spy_data is not None and not spy_data.empty:
            rs_rating, stock_return, market_return = calculate_relative_strength(data, spy_data)
        
        # Apply the 8 criteria
        criteria = {}
        criteria['1_price_above_50ma'] = current_price > ma_50
        criteria['2_price_above_150ma'] = current_price > ma_150
        criteria['3_price_above_200ma'] = current_price > ma_200
        criteria['4_50ma_above_150ma'] = ma_50 > ma_150
        criteria['5_150ma_above_200ma'] = ma_150 > ma_200
        criteria['6_200ma_trending_up'] = ma_200 > ma_200_1m_ago and ma_200 > ma_200_4m_ago
        criteria['7_price_near_52w_high'] = current_price >= (week_52_high * 0.75)  # Within 25%
        criteria['8_rs_above_70'] = rs_rating >= 70
        
        # Check if all criteria pass
        all_pass = all(criteria.values())
        
        # Stock data for output
        stock_data = {
            'ticker': ticker,
            'price': round(current_price, 2),
            'ma_50': round(ma_50, 2),
            'ma_150': round(ma_150, 2),
            'ma_200': round(ma_200, 2),
            '52w_high': round(week_52_high, 2),
            'pct_from_high': round(((current_price / week_52_high) - 1) * 100, 1),
            'rs_rating': round(rs_rating, 0),
            'stock_return_1y': round(stock_return, 1),
            'market_return_1y': round(market_return, 1),
            'criteria_passed': sum(criteria.values()),
            'all_criteria_met': all_pass
        }
        
        if verbose:
            print(f"\n{ticker}:")
            print(f"  Price: ${current_price:.2f}")
            print(f"  Criteria passed: {sum(criteria.values())}/8")
            for k, v in criteria.items():
                status = "✓" if v else "✗"
                print(f"  {status} {k}")
        
        return all_pass, criteria, stock_data
        
    except Exception as e:
        if verbose:
            print(f"Error analyzing {ticker}: {e}")
        return False, {}, {}


def scan_ticker(ticker, spy_data, verbose=False):
    """Helper function for parallel processing"""
    passes, criteria, stock_data = check_minervini_criteria(ticker, spy_data, verbose)
    return ticker, passes, criteria, stock_data


def main():
    parser = argparse.ArgumentParser(
        description='Mark Minervini SEPA Stage 2 Screener',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan S&P 500
  python minervini_sepa_screener.py --universe sp500
  
  # Scan NASDAQ 100
  python minervini_sepa_screener.py --universe nasdaq100
  
  # Scan both
  python minervini_sepa_screener.py --universe both
  
  # Scan specific tickers
  python minervini_sepa_screener.py --tickers AAPL MSFT NVDA TSLA
  
  # Show verbose output
  python minervini_sepa_screener.py --universe sp500 --verbose
  
  # Save to CSV
  python minervini_sepa_screener.py --universe sp500 --output results.csv
        """
    )
    
    parser.add_argument('--universe', choices=['sp500', 'nasdaq100', 'both'], 
                       default='sp500',
                       help='Stock universe to scan (default: sp500)')
    parser.add_argument('--tickers', nargs='+',
                       help='Specific tickers to scan (overrides --universe)')
    parser.add_argument('--output', type=str,
                       help='Output CSV file path')
    parser.add_argument('--verbose', action='store_true',
                       help='Show detailed output for each stock')
    parser.add_argument('--min-criteria', type=int, default=8,
                       help='Minimum criteria to pass (default: 8, show all)')
    parser.add_argument('--workers', type=int, default=10,
                       help='Number of parallel workers (default: 10)')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("MARK MINERVINI SEPA STAGE 2 SCREENER")
    print("8-Point Trend Template")
    print("=" * 80)
    
    # Get ticker list
    if args.tickers:
        tickers = args.tickers
        print(f"\nScanning {len(tickers)} specified tickers...")
    else:
        print(f"\nFetching {args.universe.upper()} tickers...")
        if args.universe == 'sp500':
            tickers = get_sp500_tickers()
        elif args.universe == 'nasdaq100':
            tickers = get_nasdaq100_tickers()
        else:  # both
            tickers = list(set(get_sp500_tickers() + get_nasdaq100_tickers()))
        
        print(f"Found {len(tickers)} tickers")
    
    # Download S&P 500 data for relative strength calculation
    print("\nDownloading S&P 500 benchmark data...")
    spy = yf.Ticker('SPY')
    spy_data = spy.history(period='1y')
    
    # Scan stocks in parallel
    print(f"\nScanning stocks (using {args.workers} workers)...")
    print("This may take a few minutes...\n")
    
    results = []
    passed_count = 0
    failed_count = 0
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(scan_ticker, ticker, spy_data, args.verbose): ticker 
                  for ticker in tickers}
        
        for i, future in enumerate(as_completed(futures), 1):
            ticker = futures[future]
            try:
                _, passes, criteria, stock_data = future.result()
                
                if stock_data:  # If we got valid data
                    results.append(stock_data)
                    
                    if passes:
                        passed_count += 1
                        print(f"✓ {ticker:6s} - ALL 8 CRITERIA MET - Price: ${stock_data['price']:.2f} - RS: {stock_data['rs_rating']:.0f}")
                    elif stock_data['criteria_passed'] >= args.min_criteria:
                        print(f"  {ticker:6s} - {stock_data['criteria_passed']}/8 criteria - Price: ${stock_data['price']:.2f}")
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
                    
                # Progress indicator
                if i % 50 == 0:
                    print(f"\n  Progress: {i}/{len(tickers)} stocks scanned ({passed_count} passed)\n")
                    
            except Exception as e:
                print(f"✗ {ticker:6s} - Error: {e}")
                failed_count += 1
    
    # Create results DataFrame
    if results:
        df = pd.DataFrame(results)
        df = df.sort_values('criteria_passed', ascending=False)
        
        # Filter by minimum criteria
        df_filtered = df[df['criteria_passed'] >= args.min_criteria].copy()
        
        print("\n" + "=" * 80)
        print("SCAN COMPLETE")
        print("=" * 80)
        print(f"\nTotal stocks scanned: {len(tickers)}")
        print(f"Valid data: {len(results)}")
        print(f"Failed/No data: {failed_count}")
        print(f"\nStocks meeting ALL 8 criteria: {passed_count}")
        print(f"Stocks meeting {args.min_criteria}+ criteria: {len(df_filtered)}")
        
        if not df_filtered.empty:
            print("\n" + "=" * 80)
            print("TOP CANDIDATES (Meeting minimum criteria)")
            print("=" * 80)
            print(df_filtered.to_string(index=False))
            
            # Save to CSV if requested
            if args.output:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M')
                output_file = args.output.replace('.csv', f'_{timestamp}.csv')
                df_filtered.to_csv(output_file, index=False)
                print(f"\nResults saved to: {output_file}")
        else:
            print("\nNo stocks met the minimum criteria.")
    else:
        print("\nNo valid results found.")


if __name__ == '__main__':
    main()
