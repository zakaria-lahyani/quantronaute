"""
Pytest configuration and fixtures for MT5 client tests.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any, List

import httpx

from app.clients.mt5.client import MT5Client
from app.clients.mt5.base import BaseClient
from app.clients.mt5.utils import RetryConfig
from app.clients.mt5.exceptions import MT5APIError, MT5ValidationError

from .fixtures.mock_data import (
    MOCK_ACCOUNT_INFO, MOCK_POSITIONS, MOCK_ORDERS, MOCK_SYMBOLS,
    MOCK_SYMBOL_INFO, MOCK_TICK_DATA, MOCK_HISTORICAL_DATA,
    MOCK_API_SUCCESS_RESPONSE, MOCK_HEALTH_CHECK
)


@pytest.fixture
def mock_retry_config():
    """Mock retry configuration for testing."""
    return RetryConfig(max_retries=1, base_delay=0.1, max_delay=1.0)


@pytest.fixture
def mock_base_url():
    """Mock base URL for testing."""
    return "http://localhost:8000"


@pytest.fixture
def mock_headers():
    """Mock headers for testing."""
    return {"Authorization": "Bearer test_token"}


@pytest.fixture
def mock_httpx_response():
    """Mock httpx Response object."""
    response = Mock(spec=httpx.Response)
    response.status_code = 200
    response.json.return_value = MOCK_API_SUCCESS_RESPONSE
    response.text = str(MOCK_API_SUCCESS_RESPONSE)
    return response


@pytest.fixture
def mock_httpx_error_response():
    """Mock httpx Response object for error cases."""
    response = Mock(spec=httpx.Response)
    response.status_code = 400
    response.json.return_value = {"message": "Bad Request", "error_code": "INVALID_PARAM"}
    response.text = '{"message": "Bad Request", "error_code": "INVALID_PARAM"}'
    return response


@pytest.fixture
def mock_httpx_client():
    """Mock httpx.Client."""
    client = Mock(spec=httpx.Client)
    client.request.return_value = Mock(spec=httpx.Response)
    client.request.return_value.status_code = 200
    client.request.return_value.json.return_value = MOCK_API_SUCCESS_RESPONSE
    return client


@pytest.fixture
def base_client(mock_base_url, mock_retry_config, mock_headers):
    """Create BaseClient instance for testing."""
    return BaseClient(
        base_url=mock_base_url,
        timeout=30.0,
        retry_config=mock_retry_config,
        headers=mock_headers
    )


@pytest.fixture
def mt5_client(mock_base_url, mock_retry_config, mock_headers):
    """Create MT5Client instance for testing."""
    with patch('app.clients.mt5.client.setup_logging'):
        return MT5Client(
            base_url=mock_base_url,
            timeout=30.0,
            retry_config=mock_retry_config,
            headers=mock_headers,
            enable_logging=False
        )


@pytest.fixture
def mock_account_client():
    """Mock AccountClient."""
    client = Mock()
    client.get_account_info.return_value = MOCK_ACCOUNT_INFO
    client.get_balance.return_value = {"balance": MOCK_ACCOUNT_INFO["balance"]}
    client.get_equity.return_value = {"equity": MOCK_ACCOUNT_INFO["equity"]}
    client.get_margin_info.return_value = {
        "margin": MOCK_ACCOUNT_INFO["margin"],
        "margin_free": MOCK_ACCOUNT_INFO["margin_free"],
        "margin_level": MOCK_ACCOUNT_INFO["margin_level"]
    }
    client.get_leverage.return_value = {"leverage": MOCK_ACCOUNT_INFO["leverage"]}
    return client


@pytest.fixture
def mock_positions_client():
    """Mock PositionsClient."""
    client = Mock()
    client.get_open_positions.return_value = MOCK_POSITIONS
    client.get_positions_by_symbol.return_value = [
        pos for pos in MOCK_POSITIONS if pos["symbol"] == "EURUSD"
    ]
    client.get_position_by_ticket.return_value = MOCK_POSITIONS[0]
    client.modify_position.return_value = MOCK_API_SUCCESS_RESPONSE
    client.close_position.return_value = MOCK_API_SUCCESS_RESPONSE
    client.close_all_positions.return_value = MOCK_API_SUCCESS_RESPONSE
    return client


@pytest.fixture
def mock_orders_client():
    """Mock OrdersClient."""
    client = Mock()
    client.get_pending_orders.return_value = MOCK_ORDERS
    client.create_order.return_value = MOCK_API_SUCCESS_RESPONSE
    client.create_buy_order.return_value = MOCK_API_SUCCESS_RESPONSE
    client.create_sell_order.return_value = MOCK_API_SUCCESS_RESPONSE
    client.update_pending_order.return_value = MOCK_API_SUCCESS_RESPONSE
    client.delete_pending_order.return_value = MOCK_API_SUCCESS_RESPONSE
    client.cancel_order.return_value = MOCK_API_SUCCESS_RESPONSE
    return client


@pytest.fixture
def mock_symbols_client():
    """Mock SymbolsClient."""
    client = Mock()
    client.get_all_symbols.return_value = MOCK_SYMBOLS
    client.get_symbol_info.return_value = MOCK_SYMBOL_INFO["EURUSD"]
    client.get_symbol_tick.return_value = MOCK_TICK_DATA["EURUSD"]
    client.is_symbol_tradable.return_value = {"symbol": "EURUSD", "is_tradable": True}
    client.select_symbol.return_value = {"symbol": "EURUSD", "success": True, "action": "added"}
    return client


@pytest.fixture
def mock_data_client():
    """Mock DataClient."""
    client = Mock()
    client.get_latest_bars.return_value = MOCK_HISTORICAL_DATA["bars"]
    client.get_historical_data.return_value = MOCK_HISTORICAL_DATA
    return client


@pytest.fixture
def mock_history_client():
    """Mock HistoryClient."""
    client = Mock()
    client.get_deals.return_value = []
    client.get_orders_history.return_value = []
    return client


@pytest.fixture
def patched_httpx_client(mock_httpx_client):
    """Patch httpx.Client for testing."""
    with patch('httpx.Client', return_value=mock_httpx_client):
        yield mock_httpx_client


@pytest.fixture
def patched_requests():
    """Patch all HTTP requests for isolated testing."""
    with patch('httpx.Client') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Default successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_API_SUCCESS_RESPONSE
        mock_client.request.return_value = mock_response
        
        yield mock_client


@pytest.fixture(autouse=True)
def disable_retries():
    """Disable retries for faster tests."""
    with patch('app.clients.mt5.utils.retry_sync') as mock_retry:
        mock_retry.side_effect = lambda func, config, *args, **kwargs: func(*args, **kwargs)
        yield


@pytest.fixture
def sample_position_data():
    """Sample position data for testing."""
    return {
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
        "sl": 1.0950,
        "tp": 1.1100
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing."""
    return {
        "ticket": 111222333,
        "symbol": "EURUSD",
        "volume": 0.1,
        "type": 2,  # BUY_LIMIT
        "price_open": 1.0950,
        "price_current": 1.1000,
        "sl": 1.0900,
        "tp": 1.1050,
        "comment": "Buy limit order",
        "magic": 98765
    }


@pytest.fixture
def sample_account_data():
    """Sample account data for testing."""
    return {
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
        "profit": 150.0
    }


class MockResponse:
    """Mock HTTP response for testing."""
    
    def __init__(self, json_data: Dict[str, Any], status_code: int = 200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = str(json_data)
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                message=f"HTTP {self.status_code}",
                request=Mock(),
                response=self
            )


@pytest.fixture
def mock_successful_response():
    """Mock successful API response."""
    return MockResponse(MOCK_API_SUCCESS_RESPONSE)


@pytest.fixture
def mock_error_response():
    """Mock error API response."""
    return MockResponse({
        "success": False,
        "data": None,
        "message": "Operation failed",
        "error_code": "INVALID_SYMBOL"
    }, status_code=400)


@pytest.fixture(scope="session")
def test_symbols():
    """Common test symbols."""
    return ["EURUSD", "GBPUSD", "USDJPY"]


@pytest.fixture(scope="session")
def test_timeframes():
    """Common test timeframes."""
    return ["M1", "M5", "M15", "M30", "H1", "H4", "D1"]