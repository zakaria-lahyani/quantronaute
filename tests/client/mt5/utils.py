"""
Test utilities for MT5 client tests.
"""

import json
import random
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from unittest.mock import Mock

import httpx

from app.clients.mt5.models import (
    Position, Order, Account, HistoricalBar, TickInfo, Symbol,
    CreateOrderRequest, PositionUpdateRequest, OrderType
)


class MockHTTPServer:
    """Mock HTTP server for testing MT5 API interactions."""
    
    def __init__(self):
        self.requests = []
        self.responses = {}
        self.default_response = {"success": True, "data": {}, "message": "OK"}
    
    def set_response(self, path: str, method: str, response: Dict[str, Any]):
        """Set a mock response for a specific path and method."""
        key = f"{method.upper()}:{path}"
        self.responses[key] = response
    
    def get_response(self, path: str, method: str) -> Dict[str, Any]:
        """Get mock response for a path and method."""
        key = f"{method.upper()}:{path}"
        return self.responses.get(key, self.default_response)
    
    def record_request(self, method: str, url: str, **kwargs):
        """Record a request for verification."""
        self.requests.append({
            "method": method,
            "url": url,
            "kwargs": kwargs,
            "timestamp": datetime.now()
        })
    
    def clear_requests(self):
        """Clear recorded requests."""
        self.requests.clear()
    
    def get_requests_for_path(self, path: str) -> List[Dict[str, Any]]:
        """Get all requests made to a specific path."""
        return [req for req in self.requests if path in req["url"]]


class DataGenerator:
    """Generate realistic test data for MT5 entities."""
    
    @staticmethod
    def generate_position(
        ticket: Optional[int] = None,
        symbol: str = "EURUSD",
        volume: float = 0.1,
        is_buy: bool = True,
        profit_range: tuple = (-50.0, 50.0),
        **overrides
    ) -> Dict[str, Any]:
        """Generate realistic position data."""
        base_price = 1.1000 if symbol == "EURUSD" else 1.2500
        price_open = base_price + random.uniform(-0.0050, 0.0050)
        price_current = price_open + random.uniform(-0.0020, 0.0020)
        
        position_data = {
            "ticket": ticket or random.randint(100000000, 999999999),
            "symbol": symbol,
            "volume": volume,
            "type": 0 if is_buy else 1,
            "price_open": round(price_open, 5),
            "price_current": round(price_current, 5),
            "profit": round(random.uniform(*profit_range), 2),
            "swap": round(random.uniform(-5.0, 5.0), 2),
            "commission": round(-volume * 0.7, 2),  # Typical commission
            "comment": f"Test position {symbol}",
            "magic": random.randint(10000, 99999),
            "time": datetime.now() - timedelta(hours=random.randint(1, 48)),
            "sl": round(price_open - (0.0050 if is_buy else -0.0050), 5) if random.random() > 0.3 else None,
            "tp": round(price_open + (0.0100 if is_buy else -0.0100), 5) if random.random() > 0.3 else None
        }
        
        position_data.update(overrides)
        return position_data
    
    @staticmethod
    def generate_order(
        ticket: Optional[int] = None,
        symbol: str = "EURUSD",
        volume: float = 0.1,
        order_type: str = "BUY_LIMIT",
        **overrides
    ) -> Dict[str, Any]:
        """Generate realistic order data."""
        base_price = 1.1000 if symbol == "EURUSD" else 1.2500
        price_open = base_price + random.uniform(-0.0100, 0.0100)
        
        order_data = {
            "ticket": ticket or random.randint(100000000, 999999999),
            "symbol": symbol,
            "volume": volume,
            "type": order_type,
            "price_open": round(price_open, 5),
            "price_current": round(base_price, 5),
            "sl": round(price_open - 0.0050, 5) if random.random() > 0.5 else None,
            "tp": round(price_open + 0.0100, 5) if random.random() > 0.5 else None,
            "comment": f"Test {order_type.lower()} order",
            "magic": random.randint(10000, 99999),
            "time_setup": datetime.now() - timedelta(minutes=random.randint(5, 1440)),
            "time_expiration": datetime.now() + timedelta(days=1) if random.random() > 0.3 else None
        }
        
        order_data.update(overrides)
        return order_data
    
    @staticmethod
    def generate_account(
        balance: float = 10000.0,
        equity_offset: float = 150.0,
        currency: str = "USD",
        **overrides
    ) -> Dict[str, Any]:
        """Generate realistic account data."""
        equity = balance + equity_offset
        margin = equity * random.uniform(0.01, 0.05)  # 1-5% margin usage
        margin_free = equity - margin
        margin_level = (equity / margin * 100) if margin > 0 else 0
        
        account_data = {
            "login": random.randint(10000000, 99999999),
            "trade_mode": random.choice(["DEMO", "REAL"]),
            "name": f"Test Account {random.randint(1000, 9999)}",
            "server": "TestServer-Demo",
            "currency": currency,
            "leverage": random.choice([100, 200, 500, 1000]),
            "balance": balance,
            "equity": equity,
            "margin": margin,
            "margin_free": margin_free,
            "margin_level": margin_level,
            "profit": equity_offset,
            "company": "Test Broker Ltd"
        }
        
        account_data.update(overrides)
        return account_data
    
    @staticmethod
    def generate_tick_data(
        symbol: str = "EURUSD",
        base_price: float = 1.1000,
        spread: float = 0.0002,
        **overrides
    ) -> Dict[str, Any]:
        """Generate realistic tick data."""
        bid = base_price + random.uniform(-0.0010, 0.0010)
        ask = bid + spread
        
        tick_data = {
            "symbol": symbol,
            "time": datetime.now(),
            "bid": round(bid, 5),
            "ask": round(ask, 5),
            "last": round((bid + ask) / 2, 5),
            "volume": random.randint(500, 2000),
            "flags": 6  # Typical flags value
        }
        
        tick_data.update(overrides)
        return tick_data
    
    @staticmethod
    def generate_historical_bars(
        symbol: str = "EURUSD",
        count: int = 100,
        timeframe: str = "H1",
        start_price: float = 1.1000,
        **overrides
    ) -> List[Dict[str, Any]]:
        """Generate realistic historical bar data."""
        bars = []
        current_price = start_price
        base_time = datetime.now() - timedelta(hours=count)
        
        for i in range(count):
            # Generate realistic OHLC data
            open_price = current_price
            
            # Random price movement
            price_change = random.uniform(-0.0050, 0.0050)
            close_price = open_price + price_change
            
            # High and low based on volatility
            volatility = random.uniform(0.0010, 0.0030)
            high_price = max(open_price, close_price) + random.uniform(0, volatility)
            low_price = min(open_price, close_price) - random.uniform(0, volatility)
            
            bar_data = {
                "time": base_time + timedelta(hours=i),
                "open": round(open_price, 5),
                "high": round(high_price, 5),
                "low": round(low_price, 5),
                "close": round(close_price, 5),
                "tick_volume": random.randint(800, 3000),
                "spread": random.randint(1, 5),
                "real_volume": 0
            }
            
            bar_data.update(overrides)
            bars.append(bar_data)
            current_price = close_price
        
        return bars
    
    @staticmethod
    def generate_symbol_info(
        symbol: str = "EURUSD",
        **overrides
    ) -> Dict[str, Any]:
        """Generate realistic symbol information."""
        symbol_configs = {
            "EURUSD": {"base": "EUR", "quote": "USD", "digits": 5, "point": 0.00001},
            "GBPUSD": {"base": "GBP", "quote": "USD", "digits": 5, "point": 0.00001},
            "USDJPY": {"base": "USD", "quote": "JPY", "digits": 3, "point": 0.001},
            "AUDUSD": {"base": "AUD", "quote": "USD", "digits": 5, "point": 0.00001},
        }
        
        config = symbol_configs.get(symbol, symbol_configs["EURUSD"])
        
        symbol_data = {
            "name": symbol,
            "description": f"{config['base']} vs {config['quote']}",
            "currency_base": config["base"],
            "currency_profit": config["quote"],
            "currency_margin": config["quote"],
            "digits": config["digits"],
            "point": config["point"],
            "spread": random.randint(1, 5),
            "trade_mode": "FULL",
            "volume_min": 0.01,
            "volume_max": 1000.0,
            "volume_step": 0.01
        }
        
        symbol_data.update(overrides)
        return symbol_data


class TestScenarios:
    """Predefined test scenarios for common trading situations."""
    
    @staticmethod
    def profitable_portfolio() -> Dict[str, Any]:
        """Generate data for a profitable trading portfolio."""
        account = DataGenerator.generate_account(
            balance=10000.0,
            equity_offset=500.0  # Profitable
        )
        
        positions = [
            DataGenerator.generate_position(symbol="EURUSD", profit_range=(50.0, 150.0)),
            DataGenerator.generate_position(symbol="GBPUSD", profit_range=(75.0, 200.0)),
            DataGenerator.generate_position(symbol="USDJPY", profit_range=(25.0, 100.0)),
        ]
        
        orders = [
            DataGenerator.generate_order(symbol="AUDUSD", order_type="BUY_LIMIT"),
            DataGenerator.generate_order(symbol="USDCHF", order_type="SELL_LIMIT"),
        ]
        
        return {
            "account": account,
            "positions": positions,
            "orders": orders,
            "scenario_type": "profitable_portfolio"
        }
    
    @staticmethod
    def losing_portfolio() -> Dict[str, Any]:
        """Generate data for a losing trading portfolio."""
        account = DataGenerator.generate_account(
            balance=10000.0,
            equity_offset=-800.0  # Losing money
        )
        
        positions = [
            DataGenerator.generate_position(symbol="EURUSD", profit_range=(-200.0, -50.0)),
            DataGenerator.generate_position(symbol="GBPUSD", profit_range=(-300.0, -100.0)),
            DataGenerator.generate_position(symbol="USDJPY", profit_range=(-150.0, -25.0)),
        ]
        
        orders = []  # No pending orders in losing scenario
        
        return {
            "account": account,
            "positions": positions,
            "orders": orders,
            "scenario_type": "losing_portfolio"
        }
    
    @staticmethod
    def margin_call_scenario() -> Dict[str, Any]:
        """Generate data for a margin call scenario."""
        account = DataGenerator.generate_account(
            balance=1000.0,
            equity_offset=-300.0  # Low equity
        )
        
        # Override margin calculation for margin call
        account["equity"] = 700.0
        account["margin"] = 800.0  # High margin usage
        account["margin_free"] = -100.0  # Negative free margin
        account["margin_level"] = 87.5  # Below 100% margin call level
        
        positions = [
            DataGenerator.generate_position(
                symbol="EURUSD", 
                volume=1.0,  # Large position
                profit_range=(-300.0, -200.0)
            ),
        ]
        
        return {
            "account": account,
            "positions": positions,
            "orders": [],
            "scenario_type": "margin_call"
        }
    
    @staticmethod
    def empty_account() -> Dict[str, Any]:
        """Generate data for an empty trading account."""
        account = DataGenerator.generate_account()
        
        return {
            "account": account,
            "positions": [],
            "orders": [],
            "scenario_type": "empty_account"
        }


class MockHTTPXClient:
    """Mock httpx.Client for testing HTTP interactions."""
    
    def __init__(self, responses: Optional[Dict[str, Any]] = None):
        self.responses = responses or {}
        self.requests = []
        self.default_response_data = {"success": True, "data": {}}
    
    def request(self, method: str, url: str, **kwargs) -> Mock:
        """Mock HTTP request method."""
        # Record the request
        self.requests.append({
            "method": method,
            "url": url,
            "kwargs": kwargs
        })
        
        # Create mock response
        response = Mock(spec=httpx.Response)
        
        # Find matching response
        path = url.split("/")[-1] if "/" in url else url
        key = f"{method}:{path}"
        
        response_data = self.responses.get(key, self.default_response_data)
        response.status_code = 200
        response.json.return_value = response_data
        response.text = json.dumps(response_data)
        
        return response
    
    def close(self):
        """Mock close method."""
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def create_mock_response(data: Any, success: bool = True, status_code: int = 200) -> Mock:
    """Create a mock HTTP response."""
    response = Mock(spec=httpx.Response)
    response.status_code = status_code
    
    if success:
        response_data = {"success": True, "data": data, "message": "OK"}
    else:
        response_data = {"success": False, "data": None, "message": str(data)}
    
    response.json.return_value = response_data
    response.text = json.dumps(response_data)
    
    return response


def assert_valid_position(position: Position):
    """Assert that a Position object has valid data."""
    assert isinstance(position, Position)
    assert position.ticket > 0
    assert position.symbol
    assert position.volume > 0
    assert position.type in ["BUY", "SELL", 0, 1]
    assert position.price_open > 0
    assert position.price_current > 0


def assert_valid_order(order: Order):
    """Assert that an Order object has valid data."""
    assert isinstance(order, Order)
    assert order.ticket > 0
    assert order.symbol
    assert order.type in [
        "BUY", "SELL", "BUY_LIMIT", "SELL_LIMIT",
        "BUY_STOP", "SELL_STOP", "BUY_STOP_LIMIT", "SELL_STOP_LIMIT",
        0, 1, 2, 3, 4, 5, 6, 7
    ]


def assert_valid_account(account_data: Dict[str, Any]):
    """Assert that account data is valid."""
    required_fields = ["login", "balance", "equity", "currency", "leverage"]
    
    for field in required_fields:
        assert field in account_data, f"Missing required field: {field}"
    
    assert account_data["balance"] >= 0
    assert account_data["equity"] >= 0
    assert account_data["leverage"] > 0
    assert isinstance(account_data["currency"], str)
    assert len(account_data["currency"]) == 3  # Currency code should be 3 letters


def generate_test_symbols(count: int = 10) -> List[str]:
    """Generate a list of test trading symbols."""
    major_pairs = ["EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD", "NZDUSD"]
    minor_pairs = ["EURGBP", "EURJPY", "GBPJPY", "CHFJPY", "AUDCAD", "GBPCAD"]
    exotic_pairs = ["USDTRY", "USDZAR", "USDMXN", "USDHKD", "USDSGD"]
    
    all_symbols = major_pairs + minor_pairs + exotic_pairs
    return all_symbols[:min(count, len(all_symbols))]


def wait_for_condition(condition_func, timeout: float = 5.0, interval: float = 0.1) -> bool:
    """Wait for a condition to become true within a timeout period."""
    import time
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        if condition_func():
            return True
        time.sleep(interval)
    
    return False