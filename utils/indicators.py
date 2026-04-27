"""
Technical indicators utility for trading strategy.
Implements EMA, RSI, and other common indicators.
"""
import pandas as pd
import numpy as np
from typing import Tuple


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """
    Calculate Exponential Moving Average.
    
    Args:
        data: Price series
        period: EMA period
        
    Returns:
        EMA series
    """
    return data.ewm(span=period, adjust=False).mean()


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Relative Strength Index.
    
    Args:
        data: Price series (typically close prices)
        period: RSI period (default 14)
        
    Returns:
        RSI series
    """
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi


def calculate_sma(data: pd.Series, period: int) -> pd.Series:
    """
    Calculate Simple Moving Average.
    
    Args:
        data: Price series
        period: SMA period
        
    Returns:
        SMA series
    """
    return data.rolling(window=period).mean()


def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD indicator.
    
    Args:
        data: Price series
        fast: Fast EMA period
        slow: Slow EMA period
        signal: Signal line period
        
    Returns:
        Tuple of (MACD line, Signal line, Histogram)
    """
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """
    Calculate Average True Range.
    
    Args:
        high: High price series
        low: Low price series
        close: Close price series
        period: ATR period
        
    Returns:
        ATR series
    """
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = abs(high - prev_close)
    tr3 = abs(low - prev_close)
    
    true_range = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = true_range.rolling(window=period).mean()
    
    return atr


def get_indicator_values(df: pd.DataFrame) -> dict:
    """
    Calculate all required indicators for a dataframe.
    
    Args:
        df: DataFrame with OHLC data (columns: open, high, low, close)
        
    Returns:
        Dictionary with indicator values
    """
    if len(df) < 200:
        raise ValueError("Insufficient data for indicator calculation (need at least 200 rows)")
    
    # Calculate EMAs
    ema_50 = calculate_ema(df['close'], 50)
    ema_200 = calculate_ema(df['close'], 200)
    
    # Calculate RSI
    rsi = calculate_rsi(df['close'], 14)
    
    # Get latest values
    latest = {
        'ema_50': ema_50.iloc[-1],
        'ema_200': ema_200.iloc[-1],
        'rsi': rsi.iloc[-1],
        'current_price': df['close'].iloc[-1],
        'timestamp': df.index[-1]
    }
    
    # Previous values for trend analysis
    previous = {
        'ema_50': ema_50.iloc[-2] if len(ema_50) > 1 else None,
        'ema_200': ema_200.iloc[-2] if len(ema_200) > 1 else None,
        'rsi': rsi.iloc[-2] if len(rsi) > 1 else None,
    }
    
    return {
        'latest': latest,
        'previous': previous,
        'full': {
            'ema_50': ema_50,
            'ema_200': ema_200,
            'rsi': rsi
        }
    }
