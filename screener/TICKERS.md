# Ticker Management

## Current Setup

The screener now uses **tickers.csv** as the source for all stock symbols.

### Available Indices

| Index | Tickers | Description | Exchange Suffix |
|-------|---------|-------------|-----------------|
| **S&P500** | 503 | S&P 500 companies by market cap | (none) |
| **Nasdaq100** | 101 | Nasdaq 100 tech-heavy index | (none) |
| **FTSE100** | 100 | UK's top 100 companies | `.L` (London) |

**Total unique tickers:** 617 (some overlap between indices)

## Usage

### Load by Index

```python
from src.tickers import get_tickers_by_index

sp500_tickers = get_tickers_by_index("S&P500")
nasdaq_tickers = get_tickers_by_index("Nasdaq100")
ftse_tickers = get_tickers_by_index("FTSE100")
```

### Load All

```python
from src.tickers import get_all_tickers

all_tickers = get_all_tickers()
# Returns: {"S&P500": [...], "Nasdaq100": [...], "FTSE100": [...]}
```

## Running Screens

### Current Default (S&P 500)

```bash
python run_daily.py
```

Screens all 503 S&P 500 tickers with RSI + ADX confluence filters.

### Test Mode (First 150)

```bash
python run_daily.py  # Edit max_tickers parameter in the script
```

### Detailed Breakdown

```bash
python run_daily_detailed.py
```

Shows three reports:
1. **Full confluence** (SMMA + RSI + ADX) — strictest
2. **SMMA + RSI only** — balanced
3. **SMMA + ADX only** — trend-focused

## CSV Format

```csv
#,Symbol,Company,Index
1,NVDA,Nvidia,S&P500
2,AAPL,Apple Inc.,S&P500
...
```

**Note:** Symbols are automatically converted for yfinance compatibility:
- US tickers: `BRK.B` → `BRK-B` (dots to dashes)
- FTSE100: Automatically adds `.L` suffix (London Stock Exchange)
  - `BP` → `BP.L`
  - `ULVR` → `ULVR.L`

## Updating Tickers

To update the ticker list:

1. **Replace tickers.csv** with new data
2. **Keep the format:** `#,Symbol,Company,Index`
3. **Test:**
   ```bash
   cd src && python tickers.py
   ```

## Future: Multi-Index Screening

To screen multiple indices, modify `run_daily.py`:

```python
from src.tickers import get_all_tickers

all_tickers = get_all_tickers()

for index_name, tickers in all_tickers.items():
    print(f"\n{'='*60}")
    print(f"Screening {index_name}")
    print('='*60)
    
    results = run_daily_screen(
        save_to_db=True,
        require_rsi=True,
        require_adx=False,
        tickers=tickers  # Pass custom ticker list
    )
    print(format_report(results))
```

## Performance

- **S&P 500 (503 tickers):** ~2-3 minutes
- **Nasdaq 100 (101 tickers):** ~30 seconds
- **FTSE 100 (100 tickers):** ~30 seconds
- **All indices (617 unique):** ~3-4 minutes

Data fetch is the bottleneck (Yahoo Finance API).

**Status:** ✅ All exchanges working correctly (US + London)
