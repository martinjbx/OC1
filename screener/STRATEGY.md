# Stock Screener Strategy

## Overview
Multi-indicator technical analysis screener combining SMMA crossovers with RSI confluence for high-probability buy signals.

## Indicators

### 1. SMMA Crossover (Larsson Line)
- **Fast SMMA:** 15 periods
- **Slow SMMA:** 29 periods
- **Signal:** Buy when fast crosses above slow

**Why SMMA?**
- Smoothed Moving Average reduces noise vs simple MA
- Uses Wilder's smoothing (similar to RSI calculation)
- Less whipsaw than EMA

### 2. RSI Confluence Filter
Applied to BUY signals only to ensure we're buying recovered weakness.

**Requirements (all must be met):**
1. **Current RSI: 30-70**
   - Not overbought (>70)
   - Not oversold (<30)
   - In "normal" trading range

2. **Was Recently Weak**
   - RSI was below 45 in last 15 days
   - Indicates recent selling pressure / weakness

3. **Recovering**
   - Current RSI > (Min RSI + 5 points)
   - Stock has bounced from its low
   - Buyers stepping in

**Why this works:**
- Catches stocks recovering from weakness
- Avoids chasing overbought rallies
- Confirms SMMA crossover with momentum shift

## Parameters

```python
# SMMA
FAST_PERIOD = 15
SLOW_PERIOD = 29

# RSI
RSI_PERIOD = 14
RSI_RANGE = (30, 70)
OVERSOLD_THRESHOLD = 45
RECOVERY_BUFFER = 5
LOOKBACK_DAYS = 15
```

## Signal Quality

**Strong Buy** = SMMA crossover + RSI confluence
- Both trend (SMMA) and momentum (RSI) aligned
- Stock showing strength after weakness
- Lower risk entry point

**Filtered Out:**
- SMMA crossover without RSI recovery (momentum not confirmed)
- Overbought rallies (RSI > 70)
- Stocks that never weakened (no pullback)

## Example

**TEL (TE Connectivity) - Feb 20, 2026**
- Price: $234.73
- SMMA: Fast (228.45) crossed above Slow (228.43) ✅
- RSI: Current 56.1
  - Was 32.7 on Feb 5 (oversold) ✅
  - Recovered 23.4 points (> 5) ✅
  - In normal range (30-70) ✅

**Result:** Strong buy signal with full confluence

## Database Schema

### signals table
```sql
CREATE TABLE signals (
    id INTEGER PRIMARY KEY,
    ticker TEXT,
    signal_type TEXT,  -- 'BUY' or 'SELL'
    signal_date TEXT,
    price REAL,
    smma_fast REAL,
    smma_slow REAL,
    rsi REAL,
    detected_at TIMESTAMP
)
```

### price_history table
```sql
CREATE TABLE price_history (
    id INTEGER PRIMARY KEY,
    ticker TEXT,
    date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER,
    smma_fast REAL,
    smma_slow REAL,
    rsi REAL,
    signal INTEGER,  -- 2=bullish cross, -2=bearish cross, 0=none
    created_at TIMESTAMP,
    UNIQUE(ticker, date)
)
```

## Usage

### Run Daily Scan
```bash
cd screener
source venv/bin/activate
python run_daily.py
```

### Test Single Ticker
```bash
python test_rsi.py
```

### Disable RSI Filter
```python
from src.screener import run_daily_screen

# Screen without RSI requirements
results = run_daily_screen(require_rsi_confluence=False)
```

## Future Enhancements

Potential additions for further confluence:
- Volume confirmation (above average)
- Support/resistance levels
- Sector rotation analysis
- Market regime filter (bull/bear/sideways)
- Multiple timeframe analysis

---

**Philosophy:** Quality over quantity. Better to have 2 high-probability signals than 20 marginal ones.
