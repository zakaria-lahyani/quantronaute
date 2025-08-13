"""
Pytest configuration and shared fixtures for entry manager tests.
"""

import pytest
import logging
from datetime import datetime
from unittest.mock import Mock

from app.entry_manager.manager import RiskManager
from app.utils.logger import AppLogger

from .fixtures.mock_strategies import (
    create_basic_strategy,
    create_percentage_strategy,
    create_volatility_strategy,
    create_multiple_strategies
)
from .fixtures.mock_data import (
    create_market_data_simple,
    create_market_data_trending,
    create_multi_timeframe_data
)


@pytest.fixture
def null_logger():
    """Provide a null logger for tests."""
    logger = logging.getLogger("test_logger")
    logger.setLevel(logging.CRITICAL)  # Only show critical errors
    logger.addHandler(logging.NullHandler())
    return logger


@pytest.fixture
def basic_strategy():
    """Provide a basic strategy for testing."""
    return create_basic_strategy()


@pytest.fixture
def percentage_strategy():
    """Provide a percentage-based strategy for testing."""
    return create_percentage_strategy()


@pytest.fixture
def volatility_strategy():
    """Provide a volatility-based strategy for testing."""
    return create_volatility_strategy()


@pytest.fixture
def multiple_strategies():
    """Provide multiple strategies for testing."""
    return create_multiple_strategies()


@pytest.fixture
def basic_risk_manager(basic_strategy, null_logger):
    """Provide a basic RiskManager instance."""
    strategies = {"test": basic_strategy}
    return RiskManager(
        strategies=strategies,
        symbol="EURUSD",
        pip_value=10000.0,
        logger=null_logger
    )


@pytest.fixture
def multi_strategy_risk_manager(multiple_strategies, null_logger):
    """Provide a RiskManager with multiple strategies."""
    return RiskManager(
        strategies=multiple_strategies,
        symbol="EURUSD",
        pip_value=10000.0,
        logger=null_logger
    )


@pytest.fixture
def simple_market_data():
    """Provide simple market data for testing."""
    return create_market_data_simple()


@pytest.fixture
def trending_market_data():
    """Provide trending market data for testing."""
    return create_market_data_trending()


@pytest.fixture
def multi_timeframe_market_data():
    """Provide multi-timeframe market data for testing."""
    return create_multi_timeframe_data()


@pytest.fixture
def current_time():
    """Provide current datetime for testing."""
    return datetime.now()


@pytest.fixture(autouse=True)
def setup_test_logging():
    """Setup logging for tests."""
    # Suppress debug logging during tests unless specifically needed
    AppLogger.set_level("entry-manager", logging.WARNING)
    AppLogger.set_level("position-sizer", logging.WARNING)
    AppLogger.set_level("stop-loss", logging.WARNING)
    AppLogger.set_level("take-profit", logging.WARNING)


@pytest.fixture
def mock_strategy_result():
    """Provide a mock strategy evaluation result."""
    return Mock(
        entry=Mock(long=True, short=False),
        exit=Mock(long=False, short=False)
    )


@pytest.fixture
def mock_strategy_results(mock_strategy_result):
    """Provide mock strategy results for multiple strategies."""
    return {
        "conservative": mock_strategy_result,
        "aggressive": Mock(
            entry=Mock(long=False, short=True),
            exit=Mock(long=False, short=False)
        ),
        "scalping": Mock(
            entry=Mock(long=False, short=False),
            exit=Mock(long=True, short=False)
        )
    }


# Test configuration
pytest_plugins = []


def pytest_configure(config):
    """Configure pytest settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers",
        "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", 
        "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "performance: mark test as performance-related"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit marker to unit test files
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        
        # Add integration marker to integration test files
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        
        # Add slow marker to performance tests
        if "performance" in item.name.lower() or "large" in item.name.lower():
            item.add_marker(pytest.mark.slow)
        
        # Add performance marker to performance-related tests
        if "performance" in str(item.fspath) or "performance" in item.name.lower():
            item.add_marker(pytest.mark.performance)


@pytest.fixture(scope="session")
def test_data_dir(tmp_path_factory):
    """Provide a temporary directory for test data."""
    return tmp_path_factory.mktemp("test_data")


# Performance testing helpers
@pytest.fixture
def benchmark_params():
    """Provide parameters for benchmark testing."""
    return {
        "num_strategies": 10,
        "num_calculations": 100,
        "max_execution_time": 1.0  # seconds
    }


# Parametrized fixtures for comprehensive testing
@pytest.fixture(params=["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"])
def currency_pair(request):
    """Parametrized fixture for different currency pairs."""
    return request.param


@pytest.fixture(params=[10000.0, 100.0, 1.0])
def pip_value(request):
    """Parametrized fixture for different pip values."""
    return request.param


@pytest.fixture(params=["long", "short"])
def direction(request):
    """Parametrized fixture for trade directions."""
    return request.param


@pytest.fixture(params=[1000.0, 5000.0, 10000.0, 50000.0])
def account_balance(request):
    """Parametrized fixture for different account balances."""
    return request.param