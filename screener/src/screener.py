"""Main screener logic - detect crossovers across S&P 500"""

from typing import List, Dict
import pandas as pd
from datetime import datetime, timedelta

from fetch_data import fetch_historical_data
from tickers import get_tickers_by_index, get_all_unique_tickers
from indicators import calculate_smma_crossover, detect_recent_crossover, check_rsi_confluence, check_adx_confluence
from db import init_db, save_price_data, log_signal, get_favorites


def screen_ticker(ticker: str, lookback_days: int = 1, require_rsi_confluence: bool = True, require_adx_confluence: bool = True) -> Dict:
    """
    Screen a single ticker for SMMA crossovers with RSI and ADX confluence
    
    Args:
        ticker: Stock symbol
        lookback_days: Check for crossovers in last N days (1 = today only)
        require_rsi_confluence: Require RSI to be 30-70 and recovering from oversold
        require_adx_confluence: Require ADX > 25 and trending higher
    
    Returns:
        dict with screening results or None on error
    """
    # Fetch data (need enough history to calculate SMMA 29)
    df = fetch_historical_data(ticker, period="6mo")
    
    if df is None or len(df) < 30:
        return None
    
    # Calculate indicators
    df = calculate_smma_crossover(df)
    
    # Check for recent crossover
    crossover = detect_recent_crossover(df, lookback_days=lookback_days)
    
    if crossover['has_crossover'] and crossover['days_ago'] == 0:
        # Check RSI confluence for BUY signals only
        if require_rsi_confluence and crossover['signal_type'] == 'BUY':
            rsi_check = check_rsi_confluence(df, lookback=15, oversold_threshold=45)
            if not rsi_check['meets_conditions']:
                # Skip this signal - no RSI confluence
                return None
        
        # Check ADX confluence for BUY signals only
        if require_adx_confluence and crossover['signal_type'] == 'BUY':
            adx_check = check_adx_confluence(df, lookback=5, adx_threshold=25)
            if not adx_check['meets_conditions']:
                # Skip this signal - no ADX confluence
                return None
        
        # Crossover happened today (or most recent trading day)
        result = {
            'ticker': ticker,
            'signal_type': crossover['signal_type'],
            'date': df.index[-1].strftime('%Y-%m-%d'),
            'price': crossover['price'],
            'smma_fast': crossover['smma_fast'],
            'smma_slow': crossover['smma_slow'],
            'current_position': crossover['current_position']
        }
        
        # Add RSI info if available
        if 'rsi' in df.columns:
            current_rsi = float(df['rsi'].iloc[-1]) if pd.notna(df['rsi'].iloc[-1]) else None
            result['rsi'] = current_rsi
            if require_rsi_confluence and crossover['signal_type'] == 'BUY':
                result['rsi_confluence'] = check_rsi_confluence(df, lookback=15, oversold_threshold=45)
        
        # Add ADX info if available
        if 'adx' in df.columns:
            current_adx = float(df['adx'].iloc[-1]) if pd.notna(df['adx'].iloc[-1]) else None
            result['adx'] = current_adx
            if require_adx_confluence and crossover['signal_type'] == 'BUY':
                result['adx_confluence'] = check_adx_confluence(df, lookback=5, adx_threshold=25)
        
        return result
    
    return None


def run_daily_screen(save_to_db: bool = True, max_tickers: int = None, require_adx: bool = True, require_rsi: bool = True) -> Dict[str, List[Dict]]:
    """
    Run daily screen across all tickers (S&P500, Nasdaq100, FTSE100)
    
    Args:
        save_to_db: Whether to save results to database
        max_tickers: Limit number of tickers (for testing)
        require_adx: Require ADX confluence for BUY signals
        require_rsi: Require RSI confluence for BUY signals
    
    Returns:
        dict with 'buy_signals' and 'sell_signals' lists
    """
    print(f"Starting daily screen at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if save_to_db:
        init_db()
    
    # Get all unique tickers from CSV (S&P500, Nasdaq100, FTSE100)
    tickers = get_all_unique_tickers()
    
    if not tickers:
        print("Error: No tickers loaded from CSV")
        return {'buy_signals': [], 'sell_signals': [], 'errors': []}
    
    print(f"Loaded {len(tickers)} unique tickers from all indices")
    
    if max_tickers:
        tickers = tickers[:max_tickers]
        print(f"Limiting to first {max_tickers} tickers for testing")
    
    print(f"Screening {len(tickers)} tickers...")
    
    buy_signals = []
    sell_signals = []
    errors = 0
    
    for i, ticker in enumerate(tickers, 1):
        if i % 50 == 0:
            print(f"Progress: {i}/{len(tickers)}")
        
        try:
            result = screen_ticker(ticker, lookback_days=1, require_rsi_confluence=require_rsi, require_adx_confluence=require_adx)
            
            if result:
                if result['signal_type'] == 'BUY':
                    buy_signals.append(result)
                elif result['signal_type'] == 'SELL':
                    sell_signals.append(result)
                
                # Log to database
                if save_to_db:
                    log_signal(
                        ticker=result['ticker'],
                        signal_type=result['signal_type'],
                        signal_date=result['date'],
                        price=result['price'],
                        smma_fast=result['smma_fast'],
                        smma_slow=result['smma_slow'],
                        rsi=result.get('rsi'),
                        adx=result.get('adx')
                    )
        
        except Exception as e:
            errors += 1
            if errors <= 5:  # Only print first few errors
                print(f"Error screening {ticker}: {e}")
    
    print(f"\n✅ Screen complete")
    print(f"Buy signals: {len(buy_signals)}")
    print(f"Sell signals: {len(sell_signals)}")
    print(f"Errors: {errors}")
    
    return {
        'buy_signals': buy_signals,
        'sell_signals': sell_signals,
        'total_screened': len(tickers),
        'errors': errors
    }


def format_report(results: Dict) -> str:
    """Format screening results as text report"""
    lines = []
    lines.append("=" * 50)
    lines.append("📊 DAILY STOCK SCREENER REPORT")
    lines.append(f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append(f"Strategy: SMMA 15/29 Crossover + RSI Confluence")
    lines.append(f"Universe: S&P500 + Nasdaq100 + FTSE100")
    lines.append("=" * 50)
    
    buy_signals = results['buy_signals']
    sell_signals = results['sell_signals']
    
    if buy_signals:
        lines.append(f"\n🟢 BUY SIGNALS ({len(buy_signals)})")
        lines.append("-" * 50)
        for signal in buy_signals:
            line = (f"{signal['ticker']:6s} | ${signal['price']:.2f} | "
                   f"Fast: {signal['smma_fast']:.2f} | Slow: {signal['smma_slow']:.2f}")
            if 'rsi' in signal and signal['rsi'] is not None:
                line += f" | RSI: {signal['rsi']:.1f}"
            if 'adx' in signal and signal['adx'] is not None:
                line += f" | ADX: {signal['adx']:.1f}"
            lines.append(line)
    else:
        lines.append("\n🟢 BUY SIGNALS: None")
    
    if sell_signals:
        lines.append(f"\n🔴 SELL SIGNALS ({len(sell_signals)})")
        lines.append("-" * 50)
        for signal in sell_signals:
            lines.append(
                f"{signal['ticker']:6s} | ${signal['price']:.2f} | "
                f"Fast: {signal['smma_fast']:.2f} | Slow: {signal['smma_slow']:.2f}"
            )
    else:
        lines.append("\n🔴 SELL SIGNALS: None")
    
    lines.append("\n" + "=" * 50)
    lines.append(f"Screened: {results['total_screened']} tickers")
    if results['errors'] > 0:
        lines.append(f"Errors: {results['errors']}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Test with limited tickers
    print("Running test screen (first 20 tickers)...")
    results = run_daily_screen(save_to_db=True, max_tickers=20)
    
    print("\n" + format_report(results))
