#!/usr/bin/env python3
"""
Run Minervini SEPA screener with local ticker list from CSV
"""
import pandas as pd
import sys
import os

# Read tickers from CSV
tickers_df = pd.read_csv('screener/tickers.csv', encoding='utf-8-sig')
tickers = tickers_df['Symbol'].dropna().tolist()
print(f"Loaded {len(tickers)} tickers from screener/tickers.csv")

# Limit to 704 if requested
if len(sys.argv) > 1:
    max_tickers = int(sys.argv[1])
    tickers = tickers[:max_tickers]
    print(f"Limited to first {max_tickers} tickers")

# Override get_sp500_tickers and get_nasdaq100_tickers functions
import minervini_sepa_screener
original_main = minervini_sepa_screener.main

def get_tickers_from_csv():
    return tickers

# Monkey patch the functions
minervini_sepa_screener.get_sp500_tickers = get_tickers_from_csv
minervini_sepa_screener.get_nasdaq100_tickers = lambda: []

# Override sys.argv to pass arguments to the original script
sys.argv = ['minervini_sepa_screener.py', '--universe', 'sp500', '--min-criteria', '7', '--workers', '20']

# Run the original main
original_main()
