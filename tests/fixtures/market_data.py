"""
Market data fixtures for testing.

These fixtures create mock OHLCV data for testing services.
"""

import pandas as pd
from datetime import datetime, timedelta
from typing import Optional


def create_mock_bar(
    time: Optional[datetime] = None,
    open: float = 1.0900,
    high: float = 1.0905,
    low: float = 1.0895,
    close: float = 1.0902,
    volume: float = 1000.0,
) -> pd.Series:
    """
    Create a mock OHLCV bar as pandas Series.

    Args:
        time: Bar timestamp (defaults to now)
        open: Open price
        high: High price
        low: Low price
        close: Close price
        volume: Volume

    Returns:
        pandas Series with OHLCV data
    """
    if time is None:
        time = datetime.now()

    return pd.Series({
        'time': time,
        'open': open,
        'high': high,
        'low': low,
        'close': close,
        'volume': volume,
    })


def create_mock_bars(
    num_bars: int = 10,
    start_time: Optional[datetime] = None,
    interval_minutes: int = 1,
    base_price: float = 1.0900,
    price_increment: float = 0.0001,
) -> pd.DataFrame:
    """
    Create mock OHLCV bars as pandas DataFrame.

    Args:
        num_bars: Number of bars to create
        start_time: Start time (defaults to 1 hour ago)
        interval_minutes: Minutes between bars
        base_price: Starting price
        price_increment: Price change per bar

    Returns:
        pandas DataFrame with OHLCV data
    """
    if start_time is None:
        start_time = datetime.now() - timedelta(hours=1)

    bars = []
    for i in range(num_bars):
        time = start_time + timedelta(minutes=i * interval_minutes)
        price = base_price + (i * price_increment)

        bar = {
            'time': time,
            'open': price,
            'high': price + 0.0005,
            'low': price - 0.0005,
            'close': price + 0.0002,
            'volume': 1000.0 + (i * 10),
        }
        bars.append(bar)

    return pd.DataFrame(bars)


def create_mock_bars_with_trend(
    num_bars: int = 10,
    trend: str = "up",  # "up", "down", or "sideways"
    volatility: float = 0.0005,
) -> pd.DataFrame:
    """
    Create mock bars with a specific trend.

    Args:
        num_bars: Number of bars
        trend: Trend direction ("up", "down", "sideways")
        volatility: Price volatility

    Returns:
        pandas DataFrame with trending data
    """
    start_time = datetime.now() - timedelta(hours=1)
    base_price = 1.0900

    bars = []
    price = base_price

    for i in range(num_bars):
        time = start_time + timedelta(minutes=i)

        # Apply trend
        if trend == "up":
            price += 0.0002
        elif trend == "down":
            price -= 0.0002
        # sideways: price stays roughly the same

        # Add volatility
        high = price + volatility
        low = price - volatility
        close = price + (volatility / 2)

        bar = {
            'time': time,
            'open': price,
            'high': high,
            'low': low,
            'close': close,
            'volume': 1000.0,
        }
        bars.append(bar)

    return pd.DataFrame(bars)
