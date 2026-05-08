"""Load tickers from CSV file by index"""

import pandas as pd
from pathlib import Path

TICKERS_CSV = Path(__file__).parent.parent / "tickers.csv"


def get_tickers_by_index(index_name: str = "S&P500") -> list:
    """
    Load tickers from CSV file filtered by index
    
    Args:
        index_name: One of "S&P500", "Nasdaq100", "FTSE100"
    
    Returns:
        List of ticker symbols
    """
    try:
        df = pd.read_csv(TICKERS_CSV, encoding='utf-8-sig')  # Handle BOM
        df.columns = df.columns.str.strip()  # Clean column names
        
        # Filter by index
        filtered = df[df['Index'] == index_name]
        
        # Get unique symbols (some may be duplicated across indices)
        tickers = filtered['Symbol'].dropna().unique().tolist()
        
        # Fix ticker symbols for yfinance compatibility
        tickers = [t.replace('.', '-') for t in tickers]  # BRK.B -> BRK-B
        
        # Add exchange suffix for FTSE100 (London Stock Exchange)
        if index_name == "FTSE100":
            tickers = [f"{t}.L" for t in tickers]
        
        # Sort by market cap (original order in CSV)
        return tickers
    
    except Exception as e:
        print(f"Error loading tickers from CSV: {e}")
        return []


def get_all_unique_tickers() -> list:
    """
    Get all unique tickers across all indices with proper exchange suffixes
    
    Returns:
        list: Deduplicated list of all tickers with exchange suffixes
    """
    try:
        df = pd.read_csv(TICKERS_CSV, encoding='utf-8-sig')
        df.columns = df.columns.str.strip()
        
        all_tickers = []
        seen = set()
        
        # Process each index separately to apply correct suffixes
        for _, row in df.iterrows():
            symbol = row.get('Symbol')
            index = row.get('Index')
            
            if pd.isna(symbol):
                continue
            
            # Fix ticker format
            symbol = symbol.replace('.', '-')  # BRK.B -> BRK-B
            
            # Add exchange suffix for FTSE100
            if index == 'FTSE100':
                symbol = f"{symbol}.L"
            
            # Only add if not already seen (some tickers appear in multiple indices)
            if symbol not in seen:
                all_tickers.append(symbol)
                seen.add(symbol)
        
        return all_tickers
    
    except Exception as e:
        print(f"Error loading tickers from CSV: {e}")
        return []


def get_all_tickers() -> dict:
    """
    Get all tickers grouped by index (with proper exchange suffixes)
    
    Returns:
        dict: {"S&P500": [...], "Nasdaq100": [...], "FTSE100": [...]}
    """
    result = {}
    for index_name in ["S&P500", "Nasdaq100", "FTSE100"]:
        result[index_name] = get_tickers_by_index(index_name)
    
    return result


if __name__ == "__main__":
    # Test
    print("Loading tickers from CSV...")
    
    # Test by index
    all_tickers = get_all_tickers()
    
    for index_name, tickers in all_tickers.items():
        print(f"\n{index_name}: {len(tickers)} tickers")
        print(f"  First 10: {tickers[:10]}")
    
    # Test all unique
    unique_tickers = get_all_unique_tickers()
    print(f"\n{'='*60}")
    print(f"ALL UNIQUE TICKERS: {len(unique_tickers)}")
    print(f"  First 10: {unique_tickers[:10]}")
    print(f"  Last 10: {unique_tickers[-10:]}")
