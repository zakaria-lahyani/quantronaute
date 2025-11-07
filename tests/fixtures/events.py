"""
Event fixtures for testing.

These fixtures create test events with sensible defaults.
"""

import pandas as pd
from datetime import datetime
from typing import Optional

from app.events.data_events import NewCandleEvent, DataFetchedEvent
from app.events.strategy_events import EntrySignalEvent, ExitSignalEvent
from app.events.indicator_events import IndicatorsCalculatedEvent
from tests.fixtures.market_data import create_mock_bar, create_mock_bars


def create_new_candle_event(
    symbol: str = "EURUSD",
    timeframe: str = "1",
    close: float = 1.0900,
    open: float = 1.0895,
    high: float = 1.0905,
    low: float = 1.0890,
    volume: float = 1000.0,
) -> NewCandleEvent:
    """
    Create a NewCandleEvent for testing.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        close: Close price
        open: Open price
        high: High price
        low: Low price
        volume: Volume

    Returns:
        NewCandleEvent instance
    """
    bar = create_mock_bar(
        close=close,
        open=open,
        high=high,
        low=low,
        volume=volume
    )

    return NewCandleEvent(
        symbol=symbol,
        timeframe=timeframe,
        bar=bar
    )


def create_data_fetched_event(
    symbol: str = "EURUSD",
    timeframe: str = "1",
    num_bars: int = 3,
) -> DataFetchedEvent:
    """
    Create a DataFetchedEvent for testing.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        num_bars: Number of bars

    Returns:
        DataFetchedEvent instance
    """
    bars = create_mock_bars(num_bars)

    return DataFetchedEvent(
        symbol=symbol,
        timeframe=timeframe,
        bars=bars,
        num_bars=num_bars
    )


def create_entry_signal_event(
    strategy_name: str = "test_strategy",
    symbol: str = "EURUSD",
    direction: str = "long",
    entry_price: float = 1.0900,
) -> EntrySignalEvent:
    """
    Create an EntrySignalEvent for testing.

    Args:
        strategy_name: Strategy name
        symbol: Trading symbol
        direction: Trade direction
        entry_price: Entry price

    Returns:
        EntrySignalEvent instance
    """
    return EntrySignalEvent(
        strategy_name=strategy_name,
        symbol=symbol,
        direction=direction,
        entry_price=entry_price
    )


def create_exit_signal_event(
    strategy_name: str = "test_strategy",
    symbol: str = "EURUSD",
    direction: str = "long",
    reason: str = "signal",
) -> ExitSignalEvent:
    """
    Create an ExitSignalEvent for testing.

    Args:
        strategy_name: Strategy name
        symbol: Trading symbol
        direction: Trade direction
        reason: Exit reason

    Returns:
        ExitSignalEvent instance
    """
    return ExitSignalEvent(
        strategy_name=strategy_name,
        symbol=symbol,
        direction=direction,
        reason=reason
    )


def create_indicators_calculated_event(
    symbol: str = "EURUSD",
    timeframe: str = "1",
    ema_20: float = 1.0900,
    ema_50: float = 1.0850,
    rsi: float = 65.0,
    regime: str = "bull_high",
) -> IndicatorsCalculatedEvent:
    """
    Create an IndicatorsCalculatedEvent for testing.

    Args:
        symbol: Trading symbol
        timeframe: Timeframe
        ema_20: EMA 20 value
        ema_50: EMA 50 value
        rsi: RSI value
        regime: Regime

    Returns:
        IndicatorsCalculatedEvent instance
    """
    from collections import deque

    enriched_data = {
        'ema_20': ema_20,
        'ema_50': ema_50,
        'rsi': rsi,
        'regime': regime,
        'regime_confidence': 0.85,
        'close': 1.0900,
    }

    recent_rows = {
        '1': deque([enriched_data], maxlen=6)
    }

    return IndicatorsCalculatedEvent(
        symbol=symbol,
        timeframe=timeframe,
        enriched_data=enriched_data,
        recent_rows=recent_rows
    )
