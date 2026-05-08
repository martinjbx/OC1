from src.fetch_data import fetch_historical_data
from src.indicators import calculate_smma_crossover, detect_recent_crossover

df = fetch_historical_data('AAPL', period='6mo')
df = calculate_smma_crossover(df)

print('Last 5 days:')
print(df[['close', 'smma_fast', 'smma_slow', 'signal']].tail(5))

print('\nCrossover check:')
result = detect_recent_crossover(df, lookback_days=5)
print(f"Has crossover: {result['has_crossover']}")
print(f"Signal: {result['signal_type']}")
print(f"Position: {result['current_position']}")
