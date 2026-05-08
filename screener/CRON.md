# Automated Scheduling

## Overview

Two options for automated daily screening:
1. **OpenClaw Cron** (recommended) - Integrated with OpenClaw
2. **System Cron** - Traditional Unix cron

---

## Option 1: OpenClaw Cron (Recommended)

OpenClaw has built-in cron scheduling with better integration and error handling.

### Setup

```bash
# From workspace root, add to your cron config
openclaw cron add "Stock Screener" \
  --schedule "45 21 * * 1-5" \
  --command "cd screener && source venv/bin/activate && python run_daily_telegram.py" \
  --timezone "UTC"
```

**Schedule breakdown:**
- `45 21 * * 1-5` = 21:45 UTC, Monday-Friday
- Runs after both US (21:00) and UK (16:30) markets close

### Management

```bash
# List all cron jobs
openclaw cron list

# View logs
openclaw cron logs "Stock Screener"

# Disable temporarily
openclaw cron disable "Stock Screener"

# Re-enable
openclaw cron enable "Stock Screener"

# Remove
openclaw cron remove "Stock Screener"
```

### Test Run

```bash
# Trigger manually (doesn't wait for schedule)
openclaw cron trigger "Stock Screener"

# Or run directly
cd screener
source venv/bin/activate
python run_daily_telegram.py
```

---

## Option 2: System Cron

Traditional Unix cron (if OpenClaw cron isn't available).

### Install

```bash
cd /home/Anton/.openclaw/workspace/screener
chmod +x setup_cron.sh
./setup_cron.sh
```

This adds to your user crontab:
```cron
# Stock Screener - Daily at 21:45 UTC (weekdays only)
45 21 * * 1-5 cd /home/Anton/.openclaw/workspace/screener && source venv/bin/activate && python run_daily_telegram.py >> logs/screener.log 2>&1
```

### Management

```bash
# View current crontab
crontab -l

# Edit crontab
crontab -e

# View logs
tail -f /home/Anton/.openclaw/workspace/screener/logs/screener.log
```

---

## Market Close Times (Reference)

| Market | Local Close | UTC (Winter) | UTC (Summer) |
|--------|-------------|--------------|--------------|
| **NYSE/NASDAQ** | 4:00 PM ET | 21:00 | 20:00 |
| **London (LSE)** | 4:30 PM GMT | 16:30 | 15:30 |

**Safe run time:** 21:45 UTC covers both markets year-round.

---

## Telegram Delivery

### Current Behavior

- **Signals found:** Sends detailed report with BUY/SELL signals
- **No signals:** Silent (no message sent)

### To Always Send (Even "No Signals")

Edit `run_daily_telegram.py`:

```python
# Change this line:
send_full = should_send_report(results, send_empty=False)

# To:
send_full = should_send_report(results, send_empty=True)
```

Or uncomment the summary send in the else block:

```python
else:
    summary = format_summary_report(results)
    send_telegram_message(summary)  # Uncomment this
```

---

## Testing

### Dry Run (No Telegram)

```bash
cd screener
source venv/bin/activate
python run_daily.py  # Console output only
```

### Full Test (With Telegram)

```bash
cd screener
source venv/bin/activate
python run_daily_telegram.py  # Sends to Telegram
```

### Quick Test (10 Tickers)

Edit `run_daily_telegram.py` temporarily:

```python
results = run_daily_screen(
    save_to_db=False,
    max_tickers=10,  # Add this
    require_rsi=True,
    require_adx=False
)
```

---

## Troubleshooting

### No Telegram Messages

1. **Check OpenClaw message config:**
   ```bash
   openclaw message status
   ```

2. **Test message manually:**
   ```bash
   openclaw message send --channel telegram "Test message"
   ```

3. **Check screener logs:**
   ```bash
   tail -f logs/screener.log
   ```

### Cron Not Running

1. **Check cron is installed:**
   ```bash
   openclaw cron list
   # or
   crontab -l
   ```

2. **Check timezone:**
   ```bash
   timedatectl  # System timezone
   date -u      # Current UTC time
   ```

3. **Verify virtual environment:**
   ```bash
   which python  # Should show venv/bin/python
   ```

---

## Recommended Schedule

**Daily at 21:45 UTC** (9:45 PM UTC)
- ✅ After US markets close (21:00 UTC)
- ✅ After UK markets close (16:30 UTC)
- ✅ Weekdays only (Mon-Fri)
- ✅ Accounts for daylight saving time in both regions

**Alternative schedules:**

- **US market only:** `15 21 * * 1-5` (21:15 UTC)
- **UK market only:** `45 16 * * 1-5` (16:45 UTC)
- **Twice daily (US + UK):** Add both schedules

---

## Next Steps

1. ✅ Test manual run: `python run_daily_telegram.py`
2. ✅ Install cron job (OpenClaw or system)
3. ✅ Verify first automated run tomorrow
4. ⏳ Monitor logs for a week
5. ⏳ Adjust settings based on signal frequency
