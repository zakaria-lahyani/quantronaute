"""
Mock market data for testing the entry manager.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any


def create_ohlc_bar(
    time: datetime,
    open_price: float,
    high: float,
    low: float,
    close: float,
    volume: float = 1000.0
) -> Dict[str, Any]:
    """Create a single OHLC bar."""
    return {
        "time": time,
        "open": open_price,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume
    }


def create_market_data_simple(
    current_price: float = 1.1000,
    atr_value: float = 0.0010,
    rsi_value: float = 50.0,
    timeframes: List[str] = None
) -> Dict[str, Any]:
    """Create simple market data for testing."""
    if timeframes is None:
        timeframes = ["1", "5", "15"]
    
    now = datetime.now()
    market_data = {}
    
    for tf in timeframes:
        # Create a simple bar with the current price
        market_data[tf] = [
            create_ohlc_bar(
                time=now,
                open_price=current_price - 0.0001,
                high=current_price + 0.0002,
                low=current_price - 0.0002,
                close=current_price
            )
        ]
    
    # Add indicators
    market_data["ATR"] = atr_value
    market_data["RSI"] = rsi_value
    
    return market_data


def create_market_data_trending(
    start_price: float = 1.0900,
    end_price: float = 1.1100,
    num_bars: int = 20,
    timeframe: str = "5"
) -> Dict[str, Any]:
    """Create trending market data."""
    bars = []
    price_step = (end_price - start_price) / num_bars
    base_time = datetime.now() - timedelta(minutes=num_bars * 5)
    
    for i in range(num_bars):
        time = base_time + timedelta(minutes=i * 5)
        open_price = start_price + (i * price_step)
        close = start_price + ((i + 1) * price_step)
        high = max(open_price, close) + 0.0002
        low = min(open_price, close) - 0.0001
        
        bars.append(create_ohlc_bar(
            time=time,
            open_price=open_price,
            high=high,
            low=low,
            close=close
        ))
    
    # Calculate simple ATR (just use average range for simplicity)
    total_range = sum(bar["high"] - bar["low"] for bar in bars)
    atr = total_range / len(bars)
    
    return {
        timeframe: bars,
        "ATR": atr,
        "RSI": 65.0 if end_price > start_price else 35.0  # Simplified RSI
    }


def create_market_data_volatile(
    base_price: float = 1.1000,
    volatility: float = 0.0050,
    num_bars: int = 20,
    timeframe: str = "15"
) -> Dict[str, Any]:
    """Create volatile market data."""
    import random
    random.seed(42)  # For reproducible tests
    
    bars = []
    base_time = datetime.now() - timedelta(minutes=num_bars * 15)
    
    for i in range(num_bars):
        time = base_time + timedelta(minutes=i * 15)
        
        # Add random volatility
        open_price = base_price + random.uniform(-volatility, volatility)
        close = base_price + random.uniform(-volatility, volatility)
        high = max(open_price, close) + random.uniform(0, volatility/2)
        low = min(open_price, close) - random.uniform(0, volatility/2)
        
        bars.append(create_ohlc_bar(
            time=time,
            open_price=open_price,
            high=high,
            low=low,
            close=close
        ))
    
    # Calculate ATR
    ranges = [bar["high"] - bar["low"] for bar in bars]
    atr = sum(ranges) / len(ranges)
    
    return {
        timeframe: bars,
        "ATR": atr,
        "RSI": 50.0,  # Neutral RSI for volatile market
        "volatility": volatility
    }


def create_market_data_with_indicators(
    current_price: float = 1.1000,
    indicators: Dict[str, float] = None
) -> Dict[str, Any]:
    """Create market data with specific indicator values."""
    if indicators is None:
        indicators = {
            "RSI": 45.0,
            "MACD": 0.0002,
            "ATR": 0.0015,
            "MA_50": 1.0950,
            "MA_200": 1.0900
        }
    
    now = datetime.now()
    
    # Create basic OHLC data
    market_data = {
        "1": [create_ohlc_bar(
            time=now,
            open_price=current_price - 0.0001,
            high=current_price + 0.0001,
            low=current_price - 0.0002,
            close=current_price
        )],
        "5": [create_ohlc_bar(
            time=now,
            open_price=current_price - 0.0002,
            high=current_price + 0.0002,
            low=current_price - 0.0003,
            close=current_price
        )]
    }
    
    # Add all indicators
    market_data.update(indicators)
    
    return market_data


def create_multi_timeframe_data(
    m1_price: float = 1.1000,
    m5_price: float = 1.0995,
    m15_price: float = 1.0990,
    h1_price: float = 1.0985,
    h4_price: float = 1.0980
) -> Dict[str, Any]:
    """Create market data for multiple timeframes."""
    now = datetime.now()
    
    return {
        "1": [create_ohlc_bar(
            time=now,
            open_price=m1_price - 0.0001,
            high=m1_price + 0.0001,
            low=m1_price - 0.0001,
            close=m1_price
        )],
        "5": [create_ohlc_bar(
            time=now - timedelta(minutes=5),
            open_price=m5_price - 0.0002,
            high=m5_price + 0.0002,
            low=m5_price - 0.0002,
            close=m5_price
        )],
        "15": [create_ohlc_bar(
            time=now - timedelta(minutes=15),
            open_price=m15_price - 0.0003,
            high=m15_price + 0.0003,
            low=m15_price - 0.0003,
            close=m15_price
        )],
        "60": [create_ohlc_bar(
            time=now - timedelta(hours=1),
            open_price=h1_price - 0.0004,
            high=h1_price + 0.0004,
            low=h1_price - 0.0004,
            close=h1_price
        )],
        "240": [create_ohlc_bar(
            time=now - timedelta(hours=4),
            open_price=h4_price - 0.0005,
            high=h4_price + 0.0005,
            low=h4_price - 0.0005,
            close=h4_price
        )],
        "ATR": 0.0015,
        "RSI": 52.0
    }


def create_empty_market_data() -> Dict[str, Any]:
    """Create empty market data for error testing."""
    return {}


def create_invalid_market_data() -> Dict[str, Any]:
    """Create invalid market data for error testing."""
    return {
        "1": "invalid_data",  # Should be a list
        "5": [{"invalid": "bar"}],  # Missing required fields
        "ATR": "not_a_number"  # Should be a float
    }