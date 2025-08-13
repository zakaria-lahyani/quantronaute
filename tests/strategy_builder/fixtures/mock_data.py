"""
Mock data fixtures for testing.
"""

from collections import deque
from typing import Dict
import pandas as pd

from app.strategy_builder.core.domain.enums import TimeFrameEnum


def create_mock_market_data() -> Dict[str, deque[pd.Series]]:
    """
    Create mock market data for testing.
    
    Returns:
        Dictionary of mock market data by timeframe
    """
    # Create sample data for different timeframes
    data = {
        TimeFrameEnum.M1: deque([
            pd.Series({
                'close': 1.2345,
                'high': 1.2350,
                'low': 1.2340,
                'volume': 1000,
                'rsi': 65.5,
                'previous_rsi': 62.3,
                'ma_20': 1.2340,
                'previous_ma_20': 1.2338,
                'signal_strength': 0.85,
                'previous_signal_strength': 0.80
            }),
            pd.Series({
                'close': 1.2348,
                'high': 1.2352,
                'low': 1.2343,
                'volume': 1200,
                'rsi': 67.2,
                'previous_rsi': 65.5,
                'ma_20': 1.2342,
                'previous_ma_20': 1.2340,
                'signal_strength': 0.88,
                'previous_signal_strength': 0.85
            })
        ], maxlen=100),
        
        TimeFrameEnum.M5: deque([
            pd.Series({
                'close': 1.2347,
                'high': 1.2355,
                'low': 1.2335,
                'volume': 5000,
                'rsi': 66.8,
                'previous_rsi': 64.1,
                'ma_20': 1.2341,
                'previous_ma_20': 1.2339,
                'signal_strength': 0.87,
                'previous_signal_strength': 0.82
            })
        ], maxlen=100),
        
        TimeFrameEnum.H1: deque([
            pd.Series({
                'close': 1.2350,
                'high': 1.2365,
                'low': 1.2330,
                'volume': 50000,
                'rsi': 68.5,
                'previous_rsi': 65.2,
                'ma_20': 1.2345,
                'previous_ma_20': 1.2342,
                'signal_strength': 0.90,
                'previous_signal_strength': 0.85
            })
        ], maxlen=100)
    }
    
    return data


def create_empty_market_data() -> Dict[str, deque[pd.Series]]:
    """
    Create empty market data for testing edge cases.
    
    Returns:
        Dictionary of empty deques by timeframe
    """
    return {
        TimeFrameEnum.M1: deque(maxlen=100),
        TimeFrameEnum.M5: deque(maxlen=100),
        TimeFrameEnum.H1: deque(maxlen=100)
    }


def create_minimal_market_data() -> Dict[str, deque[pd.Series]]:
    """
    Create minimal market data with just basic OHLC.
    
    Returns:
        Dictionary of minimal market data
    """
    return {
        TimeFrameEnum.M1: deque([
            pd.Series({
                'close': 1.2345,
                'high': 1.2350,
                'low': 1.2340,
                'volume': 1000
            })
        ], maxlen=100)
    }