"""
Mock data for MT5 client tests.
"""

from datetime import datetime
from typing import Dict, List, Any

from app.clients.mt5.models import (
    Position, Order, Account, HistoricalBar, TickInfo, Symbol,
    CreateOrderRequest, PositionUpdateRequest, PositionCloseRequest,
    SymbolSelectRequest, OrderType, Timeframe
)


# Mock account data
MOCK_ACCOUNT_INFO = {
    "login": 12345678,
    "trade_mode": "DEMO",
    "name": "Test Account",
    "server": "MetaQuotes-Demo",
    "currency": "USD",
    "leverage": 500,
    "balance": 10000.0,
    "equity": 10150.0,
    "margin": 250.0,
    "margin_free": 9900.0,
    "margin_level": 406.0,
    "profit": 150.0,
    "company": "MetaQuotes Ltd"
}

MOCK_BALANCE = {"balance": 10000.0}
MOCK_EQUITY = {"equity": 10150.0}
MOCK_MARGIN_INFO = {
    "margin": 250.0,
    "margin_free": 9900.0,
    "margin_level": 406.0
}
MOCK_LEVERAGE = {"leverage": 500}

# Mock position data
MOCK_POSITIONS = [
    {
        "ticket": 123456789,
        "symbol": "EURUSD",
        "volume": 0.1,
        "type": 0,  # BUY
        "price_open": 1.1000,
        "price_current": 1.1015,
        "profit": 15.0,
        "swap": 0.0,
        "commission": -0.70,
        "comment": "Test position",
        "magic": 12345,
        "time": datetime(2023, 1, 1, 12, 0, 0),
        "sl": 1.0950,
        "tp": 1.1100
    },
    {
        "ticket": 987654321,
        "symbol": "GBPUSD",
        "volume": 0.05,
        "type": 1,  # SELL
        "price_open": 1.2500,
        "price_current": 1.2485,
        "profit": 7.5,
        "swap": 0.0,
        "commission": -0.35,
        "comment": "Another test position",
        "magic": 54321,
        "time": datetime(2023, 1, 1, 14, 0, 0),
        "sl": 1.2550,
        "tp": 1.2400
    }
]

# Mock order data
MOCK_ORDERS = [
    {
        "ticket": 111222333,
        "symbol": "EURUSD",
        "volume": 0.1,
        "type": 2,  # BUY_LIMIT
        "price_open": 1.0950,
        "price_current": 1.1000,
        "sl": 1.0900,
        "tp": 1.1050,
        "comment": "Buy limit order",
        "magic": 98765,
        "time_setup": datetime(2023, 1, 1, 10, 0, 0),
        "time_expiration": datetime(2023, 1, 2, 10, 0, 0)
    },
    {
        "ticket": 444555666,
        "symbol": "GBPUSD", 
        "volume": 0.2,
        "type": 3,  # SELL_LIMIT
        "price_open": 1.2600,
        "price_current": 1.2500,
        "sl": 1.2650,
        "tp": 1.2500,
        "comment": "Sell limit order",
        "magic": 56789,
        "time_setup": datetime(2023, 1, 1, 11, 0, 0),
        "time_expiration": datetime(2023, 1, 2, 11, 0, 0)
    }
]

# Mock symbol data
MOCK_SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF"]

MOCK_SYMBOL_INFO = {
    "EURUSD": {
        "name": "EURUSD",
        "description": "Euro vs US Dollar", 
        "currency_base": "EUR",
        "currency_profit": "USD",
        "currency_margin": "USD",
        "digits": 5,
        "point": 0.00001,
        "spread": 2,
        "trade_mode": "FULL",
        "volume_min": 0.01,
        "volume_max": 1000.0,
        "volume_step": 0.01
    },
    "GBPUSD": {
        "name": "GBPUSD",
        "description": "British Pound vs US Dollar",
        "currency_base": "GBP",
        "currency_profit": "USD", 
        "currency_margin": "USD",
        "digits": 5,
        "point": 0.00001,
        "spread": 3,
        "trade_mode": "FULL",
        "volume_min": 0.01,
        "volume_max": 1000.0,
        "volume_step": 0.01
    }
}

MOCK_TICK_DATA = {
    "EURUSD": {
        "symbol": "EURUSD",
        "time": datetime(2023, 1, 1, 12, 0, 0),
        "bid": 1.1000,
        "ask": 1.1002,
        "last": 1.1001,
        "volume": 1000,
        "flags": 6
    },
    "GBPUSD": {
        "symbol": "GBPUSD",
        "time": datetime(2023, 1, 1, 12, 0, 0),
        "bid": 1.2500,
        "ask": 1.2503,
        "last": 1.2501,
        "volume": 800,
        "flags": 6
    }
}

# Mock historical data
MOCK_HISTORICAL_BARS = [
    {
        "time": datetime(2023, 1, 1, 0, 0, 0),
        "open": 1.1000,
        "high": 1.1020,
        "low": 1.0980,
        "close": 1.1015,
        "tick_volume": 1500,
        "spread": 2,
        "real_volume": 0
    },
    {
        "time": datetime(2023, 1, 1, 1, 0, 0),
        "open": 1.1015,
        "high": 1.1035,
        "low": 1.1005,
        "close": 1.1025,
        "tick_volume": 1200,
        "spread": 2,
        "real_volume": 0
    },
    {
        "time": datetime(2023, 1, 1, 2, 0, 0),
        "open": 1.1025,
        "high": 1.1040,
        "low": 1.1010,
        "close": 1.1030,
        "tick_volume": 1800,
        "spread": 2,
        "real_volume": 0
    }
]

MOCK_HISTORICAL_DATA = {
    "symbol": "EURUSD",
    "timeframe": "H1",
    "bars": MOCK_HISTORICAL_BARS,
    "count": len(MOCK_HISTORICAL_BARS)
}

# Mock API responses
MOCK_API_SUCCESS_RESPONSE = {
    "success": True,
    "data": {"message": "Operation completed successfully"},
    "message": "Success",
    "error_code": None
}

MOCK_API_ERROR_RESPONSE = {
    "success": False,
    "data": None,
    "message": "Operation failed",
    "error_code": "INVALID_SYMBOL"
}

# Mock request objects
MOCK_CREATE_ORDER_REQUEST = {
    "symbol": "EURUSD",
    "volume": 0.1,
    "order_type": OrderType.BUY,
    "price": None,
    "sl": 1.0950,
    "tp": 1.1100,
    "comment": "Test order",
    "magic": 12345
}

MOCK_POSITION_UPDATE_REQUEST = {
    "stop_loss": 1.0940,
    "take_profit": 1.1110
}

MOCK_POSITION_CLOSE_REQUEST = {
    "volume": 0.1
}

MOCK_SYMBOL_SELECT_REQUEST = {
    "symbol": "EURUSD",
    "enable": True
}

# Health check response
MOCK_HEALTH_CHECK = {
    "status": "healthy",
    "timestamp": "2023-01-01T12:00:00Z",
    "version": "1.0.0"
}

# Symbol selection responses
MOCK_SYMBOL_SELECT_RESPONSE = {
    "symbol": "EURUSD",
    "success": True,
    "action": "added"
}

MOCK_SYMBOL_TRADABLE_RESPONSE = {
    "symbol": "EURUSD", 
    "is_tradable": True
}


def get_mock_position(ticket: int = None, symbol: str = None, **overrides) -> Dict[str, Any]:
    """Get a mock position with optional overrides."""
    position = MOCK_POSITIONS[0].copy()
    if ticket:
        position["ticket"] = ticket
    if symbol:
        position["symbol"] = symbol
    position.update(overrides)
    return position


def get_mock_order(ticket: int = None, symbol: str = None, **overrides) -> Dict[str, Any]:
    """Get a mock order with optional overrides."""
    order = MOCK_ORDERS[0].copy()
    if ticket:
        order["ticket"] = ticket
    if symbol:
        order["symbol"] = symbol
    order.update(overrides)
    return order


def get_mock_account(**overrides) -> Dict[str, Any]:
    """Get mock account info with optional overrides."""
    account = MOCK_ACCOUNT_INFO.copy()
    account.update(overrides)
    return account


def get_mock_historical_bars(count: int = None, **overrides) -> List[Dict[str, Any]]:
    """Get mock historical bars with optional count and overrides."""
    bars = MOCK_HISTORICAL_BARS.copy()
    if count:
        bars = bars[:count]
    
    for bar in bars:
        bar.update(overrides)
    
    return bars


def get_mock_tick_data(symbol: str = "EURUSD", **overrides) -> Dict[str, Any]:
    """Get mock tick data with optional overrides."""
    tick = MOCK_TICK_DATA.get(symbol, MOCK_TICK_DATA["EURUSD"]).copy()
    tick.update(overrides)
    return tick


def get_mock_symbol_info(symbol: str = "EURUSD", **overrides) -> Dict[str, Any]:
    """Get mock symbol info with optional overrides."""
    info = MOCK_SYMBOL_INFO.get(symbol, MOCK_SYMBOL_INFO["EURUSD"]).copy()
    info.update(overrides)
    return info