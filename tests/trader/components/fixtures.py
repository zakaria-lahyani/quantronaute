"""
Test fixtures for trader components.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from app.clients.mt5.models.response import Position
from app.clients.mt5.models.order import PendingOrder
from app.clients.mt5.models.history import ClosedPosition
from app.strategy_builder.data.dtos import EntryDecision, ExitDecision
from app.trader.risk_manager.models import RiskEntryResult


@pytest.fixture
def mock_trader():
    """Mock trader for testing."""
    trader = Mock()
    trader.close_open_position.return_value = True
    trader.get_current_price.return_value = 3400.0
    trader.open_pending_order.return_value = [{'status': 'success', 'ticket': 12345}]
    trader.close_all_open_position.return_value = True
    trader.cancel_all_pending_orders.return_value = True
    return trader


@pytest.fixture
def mock_logger():
    """Mock logger for testing."""
    return Mock()


@pytest.fixture
def sample_positions():
    """Sample open positions."""
    return [
        Position(
            ticket=12345,
            symbol="XAUUSD",
            type=0,  # BUY
            magic=988128682,
            profit=100.0,
            swap=-5.0,
            volume=0.1,
            price_open=3390.0,
            price_current=3400.0,
            sl=3380.0,
            tp=3420.0,
            time=1234567890,
            comment=""
        ),
        Position(
            ticket=12346,
            symbol="XAUUSD",
            type=1,  # SELL
            magic=988128683,
            profit=-50.0,
            swap=-2.0,
            volume=0.2,
            price_open=3410.0,
            price_current=3400.0,
            sl=3420.0,
            tp=3390.0,
            time=1234567891,
            comment=""
        )
    ]


@pytest.fixture
def sample_pending_orders():
    """Sample pending orders."""
    return [
        PendingOrder(
            ticket=54321,
            symbol="XAUUSD",
            type=2,  # BUY_LIMIT
            magic=988128682,
            price_open=3380.0,
            price_current=3400.0,
            sl=3370.0,
            tp=3400.0,
            volume_initial=0.1,
            volume_current=0.1,
            state=1,
            comment=""
        ),
        PendingOrder(
            ticket=54322,
            symbol="XAUUSD",
            type=3,  # SELL_LIMIT
            magic=988128684,
            price_open=3420.0,
            price_current=3400.0,
            sl=3430.0,
            tp=3400.0,
            volume_initial=0.2,
            volume_current=0.2,
            state=1,
            comment=""
        )
    ]


@pytest.fixture
def sample_closed_positions():
    """Sample closed positions."""
    from datetime import datetime
    return [
        ClosedPosition(
            ticket=11111,
            symbol="XAUUSD",
            type=0,
            magic=988128680,
            profit=150.0,
            commission=-3.0,
            swap=-1.0,
            volume=0.1,
            price=3395.0,  # Close price
            time=datetime(2025, 1, 15, 10, 0, 0),
            order=11111,
            position_id=11111,
            external_id="",
            comment="",
            fee=0.0,
            reason=0,
            entry=0,
            time_msc=1234567885000
        ),
        ClosedPosition(
            ticket=11112,
            symbol="XAUUSD",
            type=1,
            magic=988128681,
            profit=-75.0,
            commission=-3.0,
            swap=-2.0,
            volume=0.2,
            price=3390.0,  # Close price
            time=datetime(2025, 1, 15, 10, 5, 0),
            order=11112,
            position_id=11112,
            external_id="",
            comment="",
            fee=0.0,
            reason=0,
            entry=0,
            time_msc=1234567895000
        )
    ]


@pytest.fixture
def sample_entry_decisions():
    """Sample entry decisions."""
    return [
        EntryDecision(
            symbol="XAUUSD",
            strategy_name="test-strategy-1",
            magic=988128682,
            direction="long",
            entry_signals="BUY_LIMIT",
            entry_price=3380.0,
            position_size=0.1,
            stop_loss=Mock(),
            take_profit=Mock(),
            decision_time=datetime(2025, 1, 15, 10, 0, 0)
        ),
        EntryDecision(
            symbol="XAUUSD",
            strategy_name="test-strategy-2",
            magic=988128685,
            direction="short",
            entry_signals="SELL_LIMIT",
            entry_price=3420.0,
            position_size=0.2,
            stop_loss=Mock(),
            take_profit=Mock(),
            decision_time=datetime(2025, 1, 15, 10, 0, 0)
        )
    ]


@pytest.fixture
def sample_exit_decisions():
    """Sample exit decisions."""
    return [
        ExitDecision(
            symbol="XAUUSD",
            strategy_name="test-strategy-1",
            magic=988128682,
            direction="long",
            decision_time=datetime(2025, 1, 15, 10, 30, 0)
        ),
        ExitDecision(
            symbol="XAUUSD",
            strategy_name="test-strategy-2",
            magic=988128683,
            direction="short",
            decision_time=datetime(2025, 1, 15, 10, 30, 0)
        )
    ]


@pytest.fixture
def sample_risk_entry():
    """Sample risk entry result."""
    return RiskEntryResult(
        group_id="test-group-123",
        limit_orders=[
            {
                'symbol': 'XAUUSD',
                'order_type': 'BUY_LIMIT',
                'volume': 0.05,
                'price': 3380.0,
                'magic': 988128682
            },
            {
                'symbol': 'XAUUSD',
                'order_type': 'BUY_LIMIT',
                'volume': 0.05,
                'price': 3375.0,
                'magic': 988128682
            }
        ],
        total_orders=2,
        total_size=0.1,
        scaled_sizes=[0.05, 0.05],
        entry_prices=[3380.0, 3375.0],
        stop_losses=[3370.0, 3365.0],
        group_stop_loss=3365.0,
        stop_loss_mode="group",
        original_risk=100.0,
        take_profit=Mock(),
        calculated_risk=95.0,
        weighted_avg_entry=3377.5,
        stop_calculation_method="price_level",
        strategy_name="test-strategy",
        magic=988128682
    )