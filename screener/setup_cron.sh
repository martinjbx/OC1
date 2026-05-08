#!/bin/bash
# Setup cron jobs for daily stock screener
# Run this script to install automated daily screening

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/run_daily_telegram.py"
LOG_DIR="$SCRIPT_DIR/logs"

# Create logs directory
mkdir -p "$LOG_DIR"

echo "=========================================="
echo "STOCK SCREENER CRON SETUP"
echo "=========================================="
echo ""
echo "This will set up automated daily screening with Telegram alerts."
echo ""
echo "Market close times (UTC):"
echo "  US Markets:  21:00 UTC (4 PM ET)"
echo "  UK Markets:  16:30 UTC (4:30 PM GMT)"
echo ""
echo "Proposed schedule:"
echo "  Daily at 21:45 UTC (9:45 PM UTC)"
echo "  → After both US and UK markets close"
echo ""
echo "Script location: $PYTHON_SCRIPT"
echo "Logs location:   $LOG_DIR"
echo ""

# Ask for confirmation
read -p "Install cron job? (y/n) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Installation cancelled"
    exit 1
fi

# Create the cron command
CRON_CMD="45 21 * * 1-5 cd $SCRIPT_DIR && source venv/bin/activate && python $PYTHON_SCRIPT >> $LOG_DIR/screener.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "run_daily_telegram.py"; then
    echo "⚠️  Cron job already exists. Remove it first:"
    echo "   crontab -e"
    exit 1
fi

# Add to crontab
(crontab -l 2>/dev/null; echo "# Stock Screener - Daily at 21:45 UTC (weekdays only)"; echo "$CRON_CMD") | crontab -

echo ""
echo "✅ Cron job installed!"
echo ""
echo "Schedule: Weekdays at 21:45 UTC (9:45 PM UTC)"
echo ""
echo "To view:   crontab -l"
echo "To edit:   crontab -e"
echo "To remove: crontab -e  (then delete the line)"
echo ""
echo "Logs: $LOG_DIR/screener.log"
echo ""
echo "Test run now:"
echo "  cd $SCRIPT_DIR && source venv/bin/activate && python $PYTHON_SCRIPT"
