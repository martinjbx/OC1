"""Test RSI and ADX calculations and confluence checks"""

from src.fetch_data import fetch_historical_data
from src.indicators import calculate_smma_crossover, check_rsi_confluence, check_adx_confluence, detect_recent_crossover

def test_ticker(ticker: str):
    """Test RSI on a specific ticker"""
    print(f"\n{'='*60}")
    print(f"Testing {ticker}")
    print('='*60)
    
    df = fetch_historical_data(ticker, period="6mo")
    if df is None:
        print(f"❌ Could not fetch data for {ticker}")
        return
    
    # Calculate indicators
    df = calculate_smma_crossover(df)
    
    # Show recent data
    print("\nLast 10 days:")
    print(df[['close', 'smma_fast', 'smma_slow', 'rsi', 'adx', 'signal']].tail(10))
    
    # Check for crossover
    crossover = detect_recent_crossover(df, lookback_days=5)
    print(f"\nCrossover check:")
    print(f"  Has crossover: {crossover['has_crossover']}")
    print(f"  Signal: {crossover['signal_type']}")
    print(f"  Position: {crossover['current_position']}")
    
    # Check RSI confluence
    rsi_check = check_rsi_confluence(df, lookback=15, oversold_threshold=45)
    print(f"\nRSI Confluence:")
    print(f"  ✓ Meets conditions: {rsi_check['meets_conditions']}")
    print(f"  Current RSI: {rsi_check['current_rsi']:.2f}")
    print(f"  Was oversold (<45): {rsi_check['was_oversold']}")
    print(f"  Is recovering: {rsi_check['is_recovering']}")
    print(f"  Min RSI in period: {rsi_check['min_rsi_in_period']:.2f}")
    print(f"  RSI slope: {rsi_check['rsi_slope']:.3f}")
    if rsi_check.get('reason'):
        print(f"  Reason: {rsi_check['reason']}")
    
    # Check ADX confluence
    adx_check = check_adx_confluence(df, lookback=5, adx_threshold=25)
    print(f"\nADX Confluence:")
    print(f"  ✓ Meets conditions: {adx_check['meets_conditions']}")
    print(f"  Current ADX: {adx_check['current_adx']:.2f}")
    print(f"  Above 25: {adx_check['above_threshold']}")
    print(f"  Is strengthening: {adx_check['is_strengthening']}")
    print(f"  ADX slope: {adx_check['adx_slope']:.3f}")
    if adx_check.get('reason'):
        print(f"  Reason: {adx_check['reason']}")
    
    # Final verdict
    if crossover['has_crossover'] and crossover['signal_type'] == 'BUY':
        if rsi_check['meets_conditions'] and adx_check['meets_conditions']:
            print(f"\n✅ {ticker}: STRONG BUY (SMMA + RSI + ADX confluence)")
        elif rsi_check['meets_conditions']:
            print(f"\n⚠️  {ticker}: BUY signal with RSI (no ADX)")
        elif adx_check['meets_conditions']:
            print(f"\n⚠️  {ticker}: BUY signal with ADX (no RSI)")
        else:
            print(f"\n⚠️  {ticker}: BUY signal but NO confluence")
    elif crossover['has_crossover'] and crossover['signal_type'] == 'SELL':
        print(f"\n🔴 {ticker}: SELL signal")
    else:
        print(f"\n⏸️  {ticker}: No signal")


if __name__ == "__main__":
    # Test a few known tickers
    test_tickers = ['AAPL', 'BRK-B', 'TEL', 'TSLA', 'NVDA']
    
    for ticker in test_tickers:
        test_ticker(ticker)
    
    print(f"\n{'='*60}")
    print("Testing complete!")
    print('='*60)
