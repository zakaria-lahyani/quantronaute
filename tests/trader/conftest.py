"""
Pytest configuration and fixtures for trader tests.
"""

import pytest
import sys
import os
from datetime import datetime
from unittest.mock import Mock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.trader.models import ScalingConfig, ScaledPosition, PositionGroup
from app.trader.risk_manager import RiskManager
from app.trader.stop_loss_calculator import MonetaryStopLossCalculator, PositionEntry
from app.strategy_builder.data.dtos import EntryDecision, StopLossResult, TakeProfitResult, TPLevel


@pytest.fixture
def scaling_config_equal():
    """Create equal scaling configuration."""
    return ScalingConfig(
        num_entries=4,
        scaling_type="equal",
        entry_spacing=0.5,
        max_risk_per_group=1000.0
    )


@pytest.fixture
def scaling_config_pyramid():
    """Create pyramid scaling configuration."""
    return ScalingConfig(
        num_entries=4,
        scaling_type="pyramid_up",
        entry_spacing=1.0,
        max_risk_per_group=1000.0
    )


@pytest.fixture
def scaling_config_custom():
    """Create custom scaling configuration."""
    return ScalingConfig(
        num_entries=3,
        scaling_type="custom",
        custom_ratios=[0.5, 0.3, 0.2],
        entry_spacing=0.5,
        max_risk_per_group=500.0
    )


@pytest.fixture
def risk_manager_equal(scaling_config_equal):
    """Create RiskManager with equal scaling."""
    return RiskManager(scaling_config_equal)


@pytest.fixture
def risk_manager_no_group_stop(scaling_config_equal):
    """Create RiskManager with individual stops."""
    return RiskManager(scaling_config_equal, group_stop_loss=False)


@pytest.fixture
def gold_entry_decision():
    """Create a gold long entry decision."""
    return EntryDecision(
        symbol='XAUUSD',
        strategy_name='gold-test',
        magic=12345,
        direction='long',
        entry_signals='BUY',
        entry_price=3000.0,
        position_size=1.0,
        stop_loss=StopLossResult(
            type='fixed',
            level=2995.0,
            trailing=False
        ),
        take_profit=TakeProfitResult(
            type='multi_target',
            targets=[
                TPLevel(level=3010.0, value=1.0, percent=60.0, move_stop=True),
                TPLevel(level=3020.0, value=2.0, percent=40.0, move_stop=False)
            ]
        ),
        decision_time=datetime.now()
    )


@pytest.fixture
def bitcoin_entry_decision():
    """Create a bitcoin short entry decision."""
    return EntryDecision(
        symbol='BTCUSD',
        strategy_name='btc-test',
        magic=67890,
        direction='short',
        entry_signals='SELL',
        entry_price=117400.0,
        position_size=1.0,
        stop_loss=StopLossResult(
            type='fixed',
            level=117900.0,  # Above entry for short
            trailing=True
        ),
        take_profit=TakeProfitResult(
            type='single',
            level=116900.0,
            source=None,
            percent=None,
            targets=None
        ),
        decision_time=datetime.now()
    )


@pytest.fixture
def monetary_entry_decision():
    """Create entry decision with monetary stop loss."""
    return EntryDecision(
        symbol='XAUUSD',
        strategy_name='monetary-test',
        magic=11111,
        direction='long',
        entry_signals='BUY',
        entry_price=3000.0,
        position_size=1.0,
        stop_loss=StopLossResult(
            type='monetary',
            level=None,  # Will be calculated
            trailing=False
        ),
        take_profit=None,
        decision_time=datetime.now()
    )


@pytest.fixture
def gold_calculator():
    """Create MonetaryStopLossCalculator for gold."""
    return MonetaryStopLossCalculator('XAUUSD')


@pytest.fixture
def bitcoin_calculator():
    """Create MonetaryStopLossCalculator for bitcoin."""
    return MonetaryStopLossCalculator('BTCUSD')


@pytest.fixture
def position_entries_equal():
    """Create equal-sized position entries."""
    return [
        PositionEntry(entry_price=3000.0, position_size=0.25),
        PositionEntry(entry_price=2995.0, position_size=0.25),
        PositionEntry(entry_price=2990.0, position_size=0.25),
        PositionEntry(entry_price=2985.0, position_size=0.25)
    ]


@pytest.fixture
def position_entries_pyramid():
    """Create pyramid-sized position entries."""
    return [
        PositionEntry(entry_price=3000.0, position_size=0.1),
        PositionEntry(entry_price=2995.0, position_size=0.2),
        PositionEntry(entry_price=2990.0, position_size=0.3),
        PositionEntry(entry_price=2985.0, position_size=0.4)
    ]


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def sample_position_group(gold_entry_decision):
    """Create a sample position group."""
    return PositionGroup(
        group_id="test-group-123",
        symbol="XAUUSD",
        strategy_name="test-strategy",
        direction="long",
        original_decision=gold_entry_decision,
        total_target_size=1.0,
        num_entries=4,
        scaling_strategy="equal",
        total_risk_amount=1000.0
    )


@pytest.fixture
def filled_positions():
    """Create filled position instances."""
    positions = []
    
    pos1 = ScaledPosition(
        position_id="pos_1",
        group_id="group_1",
        symbol="XAUUSD",
        direction="long",
        entry_price=3000.0,
        position_size=0.5
    )
    pos1.update_fill(0.5, 3000.0)
    positions.append(pos1)
    
    pos2 = ScaledPosition(
        position_id="pos_2",
        group_id="group_1",
        symbol="XAUUSD",
        direction="long",
        entry_price=2995.0,
        position_size=0.5
    )
    pos2.update_fill(0.5, 2995.0)
    positions.append(pos2)
    
    return positions


@pytest.fixture(autouse=True)
def reset_uuid_counter():
    """Reset any global counters or state between tests."""
    # This runs before each test automatically
    yield
    # Cleanup after test if needed