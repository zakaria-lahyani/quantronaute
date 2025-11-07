"""
Data-related events.

These events are published by DataFetchingService when market data is fetched.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd

from app.events.base import Event


@dataclass(frozen=True)
class DataFetchedEvent(Event):
    """
    Published when market data is successfully fetched.

    This event is published for each timeframe when streaming data is retrieved.

    Attributes:
        symbol: Trading symbol (e.g., "EURUSD")
        timeframe: Timeframe (e.g., "1", "5", "15")
        bars: DataFrame containing OHLCV data
        num_bars: Number of bars in the DataFrame
    """
    symbol: str
    timeframe: str
    bars: pd.DataFrame
    num_bars: int = 0

    def __post_init__(self):
        """Calculate num_bars from DataFrame."""
        if self.num_bars == 0:
            object.__setattr__(self, 'num_bars', len(self.bars))


@dataclass(frozen=True)
class NewCandleEvent(Event):
    """
    Published when a new candle is detected.

    This event triggers indicator calculation and regime updates.

    Attributes:
        symbol: Trading symbol (e.g., "EURUSD")
        timeframe: Timeframe (e.g., "1", "5", "15")
        bar: pandas Series containing OHLCV data for the new candle
    """
    symbol: str
    timeframe: str
    bar: pd.Series

    def get_close(self) -> float:
        """Get the close price from the bar."""
        return float(self.bar['close'])

    def get_open(self) -> float:
        """Get the open price from the bar."""
        return float(self.bar['open'])

    def get_high(self) -> float:
        """Get the high price from the bar."""
        return float(self.bar['high'])

    def get_low(self) -> float:
        """Get the low price from the bar."""
        return float(self.bar['low'])

    def get_volume(self) -> float:
        """Get the volume from the bar."""
        return float(self.bar['volume'])


@dataclass(frozen=True)
class DataFetchErrorEvent(Event):
    """
    Published when data fetching fails.

    This event indicates an error occurred while fetching market data.

    Attributes:
        symbol: Trading symbol
        timeframe: Timeframe
        error: Error message
        exception: Optional exception object
    """
    symbol: str
    timeframe: str
    error: str
    exception: Optional[Exception] = None
