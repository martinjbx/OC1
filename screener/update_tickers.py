"""Update S&P 500 ticker list"""
import json
import requests
from pathlib import Path

# Using a reliable API endpoint
url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"

try:
    import pandas as pd
    
    # Fetch with proper headers
    headers = {'User-Agent': 'Mozilla/5.0'}
    tables = pd.read_html(requests.get(url, headers=headers).text)
    
    df = tables[0]
    tickers = df['Symbol'].str.replace('.', '-').tolist()
    
    # Save to file
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    
    with open(data_dir / "sp500_tickers.json", 'w') as f:
        json.dump(tickers, f, indent=2)
    
    print(f"✅ Saved {len(tickers)} S&P 500 tickers")
    print(f"First 10: {tickers[:10]}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("Using fallback list...")
