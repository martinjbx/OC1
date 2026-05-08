"""Test the screener with a small set of tickers"""
from src.fetch_data import get_sp500_tickers
from src.screener import run_daily_screen

print("Fetching tickers...")
tickers = get_sp500_tickers()
print(f"Using {len(tickers)} tickers: {tickers}")

print("\nRunning screen on these tickers...")
results = run_daily_screen(save_to_db=True, max_tickers=None)

print("\n" + "=" * 60)
print("RESULTS:")
print("=" * 60)
if results['buy_signals']:
    print(f"\n🟢 BUY SIGNALS ({len(results['buy_signals'])})")
    for sig in results['buy_signals']:
        print(f"  {sig['ticker']}: ${sig['price']:.2f}")
else:
    print("\n🟢 No buy signals")

if results['sell_signals']:
    print(f"\n🔴 SELL SIGNALS ({len(results['sell_signals'])})")
    for sig in results['sell_signals']:
        print(f"  {sig['ticker']}: ${sig['price']:.2f}")
else:
    print("\n🔴 No sell signals")
