# Investment Screener

Daily automated stock screening with Telegram alerts using SMMA crossover + RSI confluence.

## Quick Start

```bash
# Manual run (console only)
cd /home/Anton/.openclaw/workspace/screener
source venv/bin/activate
python run_daily.py

# With Telegram delivery
python run_daily_telegram.py

# Setup automated daily runs (see SETUP.md)
./setup_cron.sh
```

**Documentation:**
- **[SETUP.md](SETUP.md)** - Telegram + Cron installation guide
- **[CRON.md](CRON.md)** - Detailed cron scheduling options
- **[TICKERS.md](TICKERS.md)** - Ticker list management

---

## Phase 1 - Multi-Market SMMA Crossover

**Goal:** Daily screening of S&P 500 stocks using SMMA 15/29 crossover ("Larsson Line")

### Strategy
- **Core indicator:** SMMA 15/29 crossover ("Larsson Line")
- **Confluence filters:**
  - **RSI (14):** Must be in 30-70 range, recovering from oversold (<45)
  - **ADX (14):** Trend strength >25 and increasing (optional)
- **Signal:** 
  - BUY: SMMA 15 crosses above SMMA 29 + RSI confluence
  - SELL: SMMA 15 crosses below SMMA 29
- **Timeframe:** Daily closes
- **Output:** Single daily Telegram report (or console)

**Current configuration:** SMMA + RSI (ADX shown as informational)

### Asset Classes (roadmap)
1. ✅ S&P 500 stocks (Phase 1)
2. ⏳ Commodity miners/ETFs
3. ⏳ Crypto (BTC, ETH, SOL, etc.)

### Tech Stack
- **Python:** Data fetching, indicator calculation, screening logic
- **Libraries:** pandas, yfinance (Yahoo Finance API - free), pandas-ta
- **Storage:** SQLite for price history + signal history
- **Scheduling:** OpenClaw cron or system cron
- **Alerts:** ✅ Telegram via OpenClaw message tool (implemented)

### Data Sources
- **Stocks:** Yahoo Finance (free, 15min delayed - fine for daily closes)
- **Crypto:** CoinGecko API (free tier) - planned
- **Ticker lists:** CSV file (617 unique tickers: S&P500 + Nasdaq100 + FTSE100) — see `TICKERS.md`
  - Auto-handles exchange suffixes (`.L` for London stocks)

### Backtest Plan
- Historical period: 2023-01-01 to 2024-12-31 (2 years)
- Metrics: Win rate, avg return per signal, max drawdown
- Validate before going live

### Project Structure
```
screener/
├── src/
│   ├── fetch_data.py      # Data retrieval
│   ├── indicators.py      # SMMA calculation
│   ├── screener.py        # Crossover detection
│   ├── report.py          # Generate Telegram report
│   └── db.py              # SQLite operations
├── data/
│   └── screener.db        # SQLite database
├── backtest/
│   └── backtest.py        # Historical validation
├── docs/
│   └── strategy.md        # Strategy details
├── tests/
└── requirements.txt
```

### Development Log

**2026-02-22 - Phase 1 Complete:**
- ✅ SMMA 15/29 crossover detection
- ✅ RSI confluence filter (oversold recovery)
- ✅ ADX trend strength indicator (optional)
- ✅ Multi-market support: S&P500 (503) + Nasdaq100 (101) + FTSE100 (100)
- ✅ Exchange suffix handling (`.L` for London stocks)
- ✅ SQLite database (price history + signal log)
- ✅ **Telegram integration** - Automated daily reports
- ✅ **Cron scheduling** - Market-aware timing (21:45 UTC daily)
- ✅ Successfully tested on all 617 tickers

**Status:** Ready for production use. Awaiting first automated run.

**Next Phase:**
- ⏳ Backtest framework (historical validation)
- ⏳ Commodity miners/ETFs
- ⏳ Crypto markets (BTC, ETH, SOL)
- ⏳ Portfolio tracking
- ⏳ Performance analytics
