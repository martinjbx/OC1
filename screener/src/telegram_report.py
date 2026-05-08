"""Telegram reporting module for OpenClaw"""

from typing import Dict, List
from datetime import datetime


def format_telegram_report(results: Dict, detailed: bool = False) -> str:
    """
    Format screening results for Telegram
    
    Args:
        results: Screener results dict
        detailed: Include full details or just summary
    
    Returns:
        Formatted message string
    """
    buy_signals = results.get('buy_signals', [])
    sell_signals = results.get('sell_signals', [])
    total_screened = results.get('total_screened', 0)
    
    lines = []
    
    # Header
    lines.append("📊 *DAILY STOCK SCREENER*")
    lines.append(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"🔍 Strategy: SMMA 15/29 + RSI")
    lines.append(f"🌍 Universe: S&P500 + Nasdaq100 + FTSE100")
    lines.append("─" * 40)
    
    # Buy signals
    if buy_signals:
        lines.append(f"\n🟢 *BUY SIGNALS* ({len(buy_signals)})")
        lines.append("")
        
        for signal in buy_signals:
            ticker = signal['ticker']
            price = signal['price']
            fast = signal['smma_fast']
            slow = signal['smma_slow']
            rsi = signal.get('rsi', 'N/A')
            adx = signal.get('adx', 'N/A')
            
            lines.append(f"*{ticker}*  ${price:.2f}")
            
            if detailed:
                lines.append(f"  Fast: {fast:.2f} | Slow: {slow:.2f}")
                lines.append(f"  RSI: {rsi:.1f} | ADX: {adx:.1f}")
            else:
                lines.append(f"  SMMA: {fast:.2f}/{slow:.2f} | RSI: {rsi:.1f}")
            
            lines.append("")
    else:
        lines.append("\n🟢 *BUY SIGNALS:* None")
    
    # Sell signals
    if sell_signals:
        lines.append(f"\n🔴 *SELL SIGNALS* ({len(sell_signals)})")
        lines.append("")
        
        for signal in sell_signals:
            ticker = signal['ticker']
            price = signal['price']
            fast = signal['smma_fast']
            slow = signal['smma_slow']
            
            lines.append(f"*{ticker}*  ${price:.2f}")
            
            if detailed:
                lines.append(f"  Fast: {fast:.2f} | Slow: {slow:.2f}")
            
            lines.append("")
    else:
        lines.append("\n🔴 *SELL SIGNALS:* None")
    
    # Footer
    lines.append("─" * 40)
    lines.append(f"📈 Screened: {total_screened} tickers")
    
    return "\n".join(lines)


def should_send_report(results: Dict, send_empty: bool = False) -> bool:
    """
    Decide whether to send the report
    
    Args:
        results: Screener results
        send_empty: Send even if no signals
    
    Returns:
        bool: Whether to send
    """
    buy_signals = results.get('buy_signals', [])
    sell_signals = results.get('sell_signals', [])
    
    if send_empty:
        return True
    
    # Only send if there are signals
    return len(buy_signals) > 0 or len(sell_signals) > 0


def format_summary_report(results: Dict) -> str:
    """
    Format a brief summary (for quiet days)
    
    Returns:
        Short summary message
    """
    buy_count = len(results.get('buy_signals', []))
    sell_count = len(results.get('sell_signals', []))
    total = results.get('total_screened', 0)
    
    if buy_count == 0 and sell_count == 0:
        return f"📊 Daily screen complete: No signals today ({total} tickers screened)"
    
    return f"📊 Daily screen: {buy_count} BUY, {sell_count} SELL ({total} tickers)"
