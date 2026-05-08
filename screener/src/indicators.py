"""Technical indicators - SMMA, RSI, and ADX calculations"""

import pandas as pd
import numpy as np


def smma(series: pd.Series, period: int) -> pd.Series:
    """
    Calculate Smoothed Moving Average (SMMA)
    Also known as Running Moving Average (RMA) or Modified Moving Average (MMA)
    
    Formula:
        SMMA(i) = (SMMA(i-1) * (period - 1) + price(i)) / period
        First value is SMA
    
    Args:
        series: Price series (typically close prices)
        period: Lookback period
    
    Returns:
        SMMA series
    """
    smma_values = np.zeros(len(series))
    smma_values[:] = np.nan
    
    # First SMMA value is simple moving average
    sma_first = series.iloc[:period].mean()
    smma_values[period - 1] = sma_first
    
    # Calculate subsequent SMMA values
    for i in range(period, len(series)):
        smma_values[i] = (smma_values[i-1] * (period - 1) + series.iloc[i]) / period
    
    return pd.Series(smma_values, index=series.index)


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index (RSI)
    Uses Wilder's smoothing method (same as SMMA)
    
    Formula:
        RSI = 100 - (100 / (1 + RS))
        RS = Average Gain / Average Loss
    
    Args:
        series: Price series (typically close prices)
        period: Lookback period (default 14)
    
    Returns:
        RSI series (0-100)
    """
    delta = series.diff()
    
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Use SMMA for average gain/loss (Wilder's smoothing)
    avg_gain = smma(gain, period)
    avg_loss = smma(loss, period)
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))
    
    return rsi_values


def adx(df: pd.DataFrame, period: int = 14) -> pd.DataFrame:
    """
    Calculate Average Directional Index (ADX) and +DI/-DI
    Uses Wilder's smoothing method (same as SMMA/RSI)
    
    ADX measures trend strength (not direction):
    - 0-25: Weak or no trend
    - 25-50: Strong trend
    - 50-75: Very strong trend
    - 75-100: Extremely strong trend
    
    Args:
        df: DataFrame with 'high', 'low', 'close' columns
        period: Lookback period (default 14)
    
    Returns:
        DataFrame with columns: plus_di, minus_di, adx
    """
    df = df.copy()
    
    # Calculate True Range (TR)
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    
    # Calculate Directional Movement (+DM and -DM)
    high_diff = df['high'] - df['high'].shift()
    low_diff = df['low'].shift() - df['low']
    
    plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
    minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)
    
    # Smooth using SMMA (Wilder's smoothing)
    atr = smma(tr, period)
    plus_dm_smooth = smma(plus_dm, period)
    minus_dm_smooth = smma(minus_dm, period)
    
    # Calculate Directional Indicators (+DI and -DI)
    plus_di = 100 * (plus_dm_smooth / atr)
    minus_di = 100 * (minus_dm_smooth / atr)
    
    # Calculate Directional Index (DX)
    dx = 100 * np.abs(plus_di - minus_di) / (plus_di + minus_di)
    
    # Calculate ADX (smoothed DX)
    adx_values = smma(dx, period)
    
    return pd.DataFrame({
        'plus_di': plus_di,
        'minus_di': minus_di,
        'adx': adx_values
    }, index=df.index)


def check_rsi_confluence(df: pd.DataFrame, lookback: int = 10, oversold_threshold: float = 40) -> dict:
    """
    Check RSI confluence conditions:
    1. Current RSI between 30-70
    2. RSI recovering from weak/oversold (was below threshold recently, now trending up)
    
    Args:
        df: DataFrame with 'rsi' column
        lookback: Days to check for oversold recovery
        oversold_threshold: RSI threshold for considering "weak" (default 40)
    
    Returns:
        dict with: {
            'meets_conditions': bool,
            'current_rsi': float,
            'was_oversold': bool,
            'is_recovering': bool,
            'min_rsi_in_period': float,
            'rsi_slope': float  # positive = trending up
        }
    """
    if df.empty or 'rsi' not in df.columns:
        return {'meets_conditions': False, 'reason': 'No RSI data'}
    
    recent = df.tail(lookback)
    current_rsi = float(recent['rsi'].iloc[-1]) if pd.notna(recent['rsi'].iloc[-1]) else None
    
    if current_rsi is None:
        return {'meets_conditions': False, 'reason': 'Current RSI is NaN'}
    
    # Check if RSI in valid range (30-70)
    in_range = 30 <= current_rsi <= 70
    
    # Check if RSI was weak/oversold recently
    min_rsi = float(recent['rsi'].min())
    was_oversold = min_rsi < oversold_threshold
    
    # Check if RSI is recovering (current RSI > minimum RSI in period + some buffer)
    # This means the stock has bounced from its weakness
    recovery_buffer = 5  # RSI needs to be at least 5 points above the low
    is_recovering = current_rsi > (min_rsi + recovery_buffer)
    
    # Also calculate slope for informational purposes
    rsi_values = recent['rsi'].dropna().tail(5)
    if len(rsi_values) >= 3:
        x = np.arange(len(rsi_values))
        slope = np.polyfit(x, rsi_values.values, 1)[0]
    else:
        slope = 0
    
    meets_conditions = in_range and was_oversold and is_recovering
    
    return {
        'meets_conditions': meets_conditions,
        'current_rsi': current_rsi,
        'was_oversold': was_oversold,
        'is_recovering': is_recovering,
        'min_rsi_in_period': min_rsi,
        'rsi_slope': float(slope),
        'reason': None if meets_conditions else f"Range:{in_range} Oversold:{was_oversold} Recovering:{is_recovering}"
    }


def check_adx_confluence(df: pd.DataFrame, lookback: int = 5, adx_threshold: float = 25) -> dict:
    """
    Check ADX confluence conditions:
    1. Current ADX > threshold (strong trend)
    2. ADX trending higher (trend strengthening)
    
    Args:
        df: DataFrame with 'adx' column
        lookback: Days to check for trend direction
        adx_threshold: Minimum ADX value (default 25 = strong trend)
    
    Returns:
        dict with: {
            'meets_conditions': bool,
            'current_adx': float,
            'above_threshold': bool,
            'is_strengthening': bool,
            'adx_slope': float  # positive = strengthening
        }
    """
    if df.empty or 'adx' not in df.columns:
        return {'meets_conditions': False, 'reason': 'No ADX data'}
    
    recent = df.tail(lookback + 5)  # Need extra for slope calculation
    current_adx = float(recent['adx'].iloc[-1]) if pd.notna(recent['adx'].iloc[-1]) else None
    
    if current_adx is None:
        return {'meets_conditions': False, 'reason': 'Current ADX is NaN'}
    
    # Check if ADX above threshold
    above_threshold = current_adx > adx_threshold
    
    # Check if ADX is trending higher (simple slope)
    adx_values = recent['adx'].dropna().tail(lookback)
    if len(adx_values) >= 3:
        x = np.arange(len(adx_values))
        slope = np.polyfit(x, adx_values.values, 1)[0]
        is_strengthening = slope > 0
    else:
        is_strengthening = False
        slope = 0
    
    meets_conditions = above_threshold and is_strengthening
    
    return {
        'meets_conditions': meets_conditions,
        'current_adx': current_adx,
        'above_threshold': above_threshold,
        'is_strengthening': is_strengthening,
        'adx_slope': float(slope),
        'reason': None if meets_conditions else f"Above{adx_threshold}:{above_threshold} Strengthening:{is_strengthening}"
    }


def calculate_smma_crossover(df: pd.DataFrame, fast_period: int = 15, slow_period: int = 29, rsi_period: int = 14, adx_period: int = 14) -> pd.DataFrame:
    """
    Calculate SMMA crossover signals (Larsson Line), RSI, and ADX
    
    Args:
        df: DataFrame with 'close', 'high', 'low' columns
        fast_period: Fast SMMA period (default 15)
        slow_period: Slow SMMA period (default 29)
        rsi_period: RSI period (default 14)
        adx_period: ADX period (default 14)
    
    Returns:
        DataFrame with added columns: smma_fast, smma_slow, rsi, adx, plus_di, minus_di, signal
        signal: 1 = bullish (fast above slow), -1 = bearish (fast below slow), 0 = neutral
    """
    df = df.copy()
    
    # Calculate SMAs
    df['smma_fast'] = smma(df['close'], fast_period)
    df['smma_slow'] = smma(df['close'], slow_period)
    
    # Calculate RSI
    df['rsi'] = rsi(df['close'], rsi_period)
    
    # Calculate ADX and directional indicators
    adx_data = adx(df, adx_period)
    df['adx'] = adx_data['adx']
    df['plus_di'] = adx_data['plus_di']
    df['minus_di'] = adx_data['minus_di']
    
    # Determine position (1 = fast above slow, -1 = fast below slow)
    df['position'] = np.where(df['smma_fast'] > df['smma_slow'], 1, -1)
    
    # Detect crossovers (change in position)
    df['signal'] = df['position'].diff()
    # signal: 2 = bullish crossover (fast crossed above slow)
    #        -2 = bearish crossover (fast crossed below slow)
    #         0 = no crossover
    
    return df


def detect_recent_crossover(df: pd.DataFrame, lookback_days: int = 5) -> dict:
    """
    Detect if a crossover occurred in the last N days
    
    Args:
        df: DataFrame with signal column from calculate_smma_crossover
        lookback_days: Number of recent days to check
    
    Returns:
        dict with: {
            'has_crossover': bool,
            'signal_type': 'BUY'|'SELL'|None,
            'days_ago': int,
            'price': float,
            'smma_fast': float,
            'smma_slow': float
        }
    """
    recent = df.tail(lookback_days)
    
    # Find crossovers (signal == 2 or -2)
    bullish = recent[recent['signal'] == 2]
    bearish = recent[recent['signal'] == -2]
    
    result = {
        'has_crossover': False,
        'signal_type': None,
        'days_ago': None,
        'price': None,
        'smma_fast': None,
        'smma_slow': None,
        'current_position': None
    }
    
    # Most recent crossover
    if not bullish.empty or not bearish.empty:
        if not bullish.empty:
            last_bull = bullish.index[-1]
            last_bull_idx = df.index.get_loc(last_bull)
        else:
            last_bull_idx = -1
        
        if not bearish.empty:
            last_bear = bearish.index[-1]
            last_bear_idx = df.index.get_loc(last_bear)
        else:
            last_bear_idx = -1
        
        if last_bull_idx > last_bear_idx:
            # Most recent is bullish
            crossover_date = bullish.index[-1]
            result['signal_type'] = 'BUY'
        else:
            # Most recent is bearish
            crossover_date = bearish.index[-1]
            result['signal_type'] = 'SELL'
        
        crossover_idx = df.index.get_loc(crossover_date)
        days_ago = len(df) - crossover_idx - 1
        
        result['has_crossover'] = True
        result['days_ago'] = days_ago
        result['price'] = float(df.loc[crossover_date, 'close'])
        result['smma_fast'] = float(df.loc[crossover_date, 'smma_fast'])
        result['smma_slow'] = float(df.loc[crossover_date, 'smma_slow'])
    
    # Add current position
    if not df.empty:
        last_row = df.iloc[-1]
        if pd.notna(last_row['position']):
            result['current_position'] = 'BULLISH' if last_row['position'] == 1 else 'BEARISH'
    
    return result


if __name__ == "__main__":
    # Test with sample data
    from fetch_data import fetch_historical_data
    
    print("Testing SMMA, RSI, and ADX calculation with AAPL...")
    df = fetch_historical_data("AAPL", period="1y")
    
    if df is not None:
        df = calculate_smma_crossover(df)
        print("\nLast 10 days:")
        print(df[['close', 'smma_fast', 'smma_slow', 'rsi', 'adx', 'signal']].tail(10))
        
        print("\nRecent crossover check:")
        crossover = detect_recent_crossover(df, lookback_days=5)
        print(crossover)
        
        print("\nRSI confluence check:")
        rsi_check = check_rsi_confluence(df, lookback=15, oversold_threshold=45)
        for key, value in rsi_check.items():
            print(f"  {key}: {value}")
        
        print("\nADX confluence check:")
        adx_check = check_adx_confluence(df, lookback=5, adx_threshold=25)
        for key, value in adx_check.items():
            print(f"  {key}: {value}")
