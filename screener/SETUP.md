# Setup Guide - Telegram + Cron

## ✅ What's Ready

1. **Telegram Integration** ✅
   - Message formatting with Markdown
   - Buy/Sell signal reports
   - Summary when no signals
   
2. **Cron Scheduling** ✅
   - Daily automated runs
   - Market-aware timing
   - Weekdays only (Mon-Fri)

3. **All Tickers** ✅
   - S&P 500: 503 stocks
   - Nasdaq 100: 101 stocks
   - FTSE 100: 100 stocks (UK with `.L` suffix)
   - Total: 617 unique tickers

---

## Quick Start

### 1. Test Telegram Message (Manual)

```bash
cd /home/Anton/.openclaw/workspace/screener
source venv/bin/activate
python test_telegram.py
```

This screens 50 tickers and shows you the Telegram message format.

### 2. Full Manual Run

```bash
# Console only (no Telegram)
python run_daily.py

# With Telegram delivery
python run_daily_telegram.py
```

### 3. Install Automated Schedule

**Option A: OpenClaw Cron (Recommended)**

If OpenClaw has cron support, use this command from the OpenClaw CLI or create a cron entry:

```bash
# Schedule: Daily at 21:45 UTC, weekdays only
# This is after both US (21:00) and UK (16:30) markets close

# As a cron expression:
# 45 21 * * 1-5 = 9:45 PM UTC, Monday-Friday
```

Ask me to set this up via OpenClaw's cron system, or:

**Option B: System Cron**

```bash
cd /home/Anton/.openclaw/workspace/screener
./setup_cron.sh
```

This adds to your user crontab:
```
45 21 * * 1-5 cd /home/Anton/.openclaw/workspace/screener && source venv/bin/activate && python run_daily_telegram.py >> logs/screener.log 2>&1
```

---

## Message Behavior

### Current Settings

- **With signals:** Sends detailed report (BUY/SELL)
- **No signals:** Silent (no message)

### To Always Send (Even "No Signals")

Edit `run_daily_telegram.py` line 50:

```python
# Change:
send_full = should_send_report(results, send_empty=False)

# To:
send_full = should_send_report(results, send_empty=True)
```

---

## Schedule Details

### Recommended: 21:45 UTC (9:45 PM UTC)

**Why this time?**
- ✅ US markets close at 21:00 UTC (4 PM ET)
- ✅ UK markets close at 16:30 UTC (4:30 PM GMT)
- ✅ 45 minutes buffer for data settlement
- ✅ Works year-round (accounts for daylight saving)

**Your timezone (Europe/London):**
- **Winter (GMT):** 21:45 UTC = 9:45 PM local
- **Summer (BST):** 21:45 UTC = 10:45 PM local

### Alternative Schedules

**US markets only (earlier):**
```
15 21 * * 1-5  # 21:15 UTC (9:15 PM UTC)
```

**UK markets only (much earlier):**
```
45 16 * * 1-5  # 16:45 UTC (4:45 PM UTC)
```

**Twice daily (US + UK separately):**
```
45 16 * * 1-5  # UK close
15 21 * * 1-5  # US close
```

---

## Files Reference

| File | Purpose |
|------|---------|
| `run_daily.py` | Console-only screener (no Telegram) |
| `run_daily_telegram.py` | Screener with Telegram delivery (for cron) |
| `run_for_agent.py` | Agent-friendly output format |
| `test_telegram.py` | Test message format (50 tickers) |
| `setup_cron.sh` | System cron installer |
| `CRON.md` | Detailed cron documentation |

---

## Monitoring

### Check Logs (System Cron)

```bash
# View recent logs
tail -f /home/Anton/.openclaw/workspace/screener/logs/screener.log

# View last 50 lines
tail -50 /home/Anton/.openclaw/workspace/screener/logs/screener.log
```

### Check Cron Status

```bash
# System cron
crontab -l

# OpenClaw cron (if available)
openclaw cron list
openclaw cron logs "Stock Screener"
```

### Check Database

```bash
sqlite3 /home/Anton/.openclaw/workspace/screener/data/screener.db "SELECT * FROM signals ORDER BY signal_date DESC LIMIT 10;"
```

---

## Troubleshooting

### No Telegram Messages Received

1. **Check if signals were found:**
   ```bash
   tail -20 logs/screener.log
   ```
   Look for "Buy signals: X" — if 0, no message is sent (by design)

2. **Test manually:**
   ```bash
   cd /home/Anton/.openclaw/workspace/screener
   source venv/bin/activate
   python run_daily_telegram.py
   ```

3. **Verify Telegram is working:**
   From OpenClaw, send a test:
   ```
   Send me a test message via Telegram
   ```

### Cron Not Running

1. **Check cron is installed:**
   ```bash
   crontab -l | grep screener
   ```

2. **Check time/timezone:**
   ```bash
   date -u  # Current UTC time
   ```

3. **Verify script path is correct:**
   ```bash
   ls -l /home/Anton/.openclaw/workspace/screener/run_daily_telegram.py
   ```

### Script Errors

1. **Check Python environment:**
   ```bash
   cd /home/Anton/.openclaw/workspace/screener
   source venv/bin/activate
   which python  # Should show venv/bin/python
   ```

2. **Test dependencies:**
   ```bash
   python -c "import yfinance; print('OK')"
   ```

3. **Run with verbose output:**
   ```bash
   python run_daily_telegram.py 2>&1 | tee debug.log
   ```

---

## Customization

### Change Signal Filters

Edit `run_daily_telegram.py`:

```python
results = run_daily_screen(
    save_to_db=True,
    max_tickers=None,      # Limit for testing
    require_rsi=True,      # RSI confluence (recommended)
    require_adx=False      # ADX confluence (optional, stricter)
)
```

**Filter combinations:**
- `require_rsi=True, require_adx=False` → Balanced (current)
- `require_rsi=True, require_adx=True` → Very strict (fewer signals)
- `require_rsi=False, require_adx=False` → Pure SMMA crossover (more signals)

### Change Report Detail Level

Edit `run_daily_telegram.py`:

```python
message = format_telegram_report(results, detailed=False)

# Change to:
message = format_telegram_report(results, detailed=True)
```

**Detailed mode includes:**
- Separate Fast/Slow SMMA values
- Both RSI and ADX values
- More spacing

---

## Next Steps

1. ✅ **Test manual run:** Verify Telegram delivery works
2. ✅ **Install cron:** Choose OpenClaw or system cron
3. ⏳ **Wait for first run:** Should trigger tomorrow at 21:45 UTC
4. ⏳ **Monitor for a week:** Check logs and message delivery
5. ⏳ **Adjust filters:** Based on signal frequency (too many/few?)

---

## Example Output

### With Signals
```
📊 DAILY STOCK SCREENER
📅 2026-02-22 22:33 UTC
🔍 Strategy: SMMA 15/29 + RSI
🌍 Universe: S&P500 + Nasdaq100 + FTSE100
────────────────────────────────────────

🟢 BUY SIGNALS (2)

BRK-B  $498.20
  SMMA: 495.71/495.66 | RSI: 52.7

AAPL  $180.45
  SMMA: 178.30/178.15 | RSI: 48.2


🔴 SELL SIGNALS: None
────────────────────────────────────────
📈 Screened: 617 tickers
```

### No Signals (Silent by default)
No message sent. To change, edit `run_daily_telegram.py` (see "Message Behavior" above).

---

## Support

Questions? Ask me:
- "Show me the cron schedule"
- "Test the screener with Telegram"
- "Change the signal filters"
- "Why didn't I get a message?"
