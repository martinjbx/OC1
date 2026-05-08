"""Data fetching module - Yahoo Finance via yfinance"""

import yfinance as yf
import pandas as pd
from typing import List, Optional


def get_sp500_tickers() -> List[str]:
    """
    Fetch current S&P 500 ticker list
    Using yfinance's built-in S&P 500 ticker fetcher as fallback
    """
    try:
        # Try to get from a more reliable source
        sp500 = yf.Ticker("^GSPC")
        
        # For now, use a static approach - we'll fetch the full list separately
        # This is more reliable than scraping Wikipedia
        import json
        from pathlib import Path
        
        tickers_file = Path(__file__).parent.parent / "data" / "sp500_tickers.json"
        
        if tickers_file.exists():
            with open(tickers_file, 'r') as f:
                return json.load(f)
        else:
            # Return a small test set for now
            print("Using test ticker set. Run update_tickers.py to fetch full list.")
            return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 
                    'META', 'TSLA', 'BRK-B', 'JPM', 'V']
    
    except Exception as e:
        print(f"Error fetching tickers: {e}")
        return []


def fetch_historical_data(
    ticker: str,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    period: str = "1y"
) -> Optional[pd.DataFrame]:
    """Fetch historical daily data for a ticker"""
    try:
        stock = yf.Ticker(ticker)
        if start_date and end_date:
            df = stock.history(start=start_date, end=end_date)
        else:
            df = stock.history(period=period)
        
        if df.empty:
            return None
        
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high', 
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        return df[['open', 'high', 'low', 'close', 'volume']]
    
    except Exception as e:
        return None


def fetch_latest_close(ticker: str) -> Optional[float]:
    """Fetch most recent closing price"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
        return None
    except:
        return None


if __name__ == "__main__":
    print("Testing data fetch...")
    print("\nFetching AAPL data...")
    df = fetch_historical_data("AAPL", period="1mo")
    
    if df is not None:
        print(f"✅ Retrieved {len(df)} days")
        print(df.tail(3))
    else:
        print("❌ Failed to fetch data")
