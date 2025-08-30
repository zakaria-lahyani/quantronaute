"""Fixtures and mock data for trader tests."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock
from typing import List

from app.clients.mt5.models.order import PendingOrder
from app.clients.mt5.models.response import Position, Order, ClosedPosition
from app.trader.trading_context import MarketState, TradingContext
from app.trader.suspension_store import SuspensionStore, SuspendedItem
from app.strategy_builder.data.dtos import (
    EntryDecision, ExitDecision, StopLoss, TakeProfit, Trades
)


# Sample positions
@pytest.fixture
def sample_position():
    """Create a sample position."""
    return Position(
        ticket=12345,
        symbol="XAUUSD",
        volume=0.1,
        type=0,  # BUY
        price_open=2500.0,
        price_current=2505.0,
        profit=50.0,
        swap=0.0,
        commission=0.0,
        comment="Test position",
        magic=123456,
        sl=2490.0,
        tp=2520.0
    )


@pytest.fixture
def sample_positions():
    """Create sample positions list."""
    return [
        Position(
            ticket=12345,
            symbol="XAUUSD",
            volume=0.1,
            type=0,  # BUY
            price_open=2500.0,
            price_current=2505.0,
            profit=50.0,
            swap=0.0,
            commission=0.0,
            comment="Test position 1",
            magic=123456,
            sl=2490.0,
            tp=2520.0
        ),
        Position(
            ticket=12346,
            symbol="XAUUSD",
            volume=0.2,
            type=1,  # SELL
            price_open=2510.0,
            price_current=2505.0,
            profit=100.0,
            swap=0.0,
            commission=0.0,
            comment="Test position 2",
            magic=123457,
            sl=2520.0,
            tp=2490.0
        )
    ]


# Sample orders
@pytest.fixture
def sample_order():
    """Create a sample order."""
    return Order(
        ticket=54321,
        symbol="XAUUSD",
        volume=0.1,
        type=2,  # BUY_LIMIT
        price_open=2495.0,
        price_current=2495.0,
        sl=2485.0,
        tp=2515.0,
        comment="Test order",
        magic=123456,
        volume_initial=0.1,
        volume_current=0.1
    )


@pytest.fixture
def sample_pending_order():
    """Create a sample pending order."""
    return PendingOrder(
        ticket=54321,
        symbol="XAUUSD",
        type=2,  # BUY_LIMIT
        price_open=2495.0,
        price_current=2495.0,
        sl=2485.0,
        tp=2515.0,
        volume_initial=0.1,
        volume_current=0.1,
        state=1,
        magic=123456,
        comment="Test pending order"
    )


@pytest.fixture
def sample_pending_orders():
    """Create sample pending orders list."""
    return [
        PendingOrder(
            ticket=54321,
            symbol="XAUUSD",
            type=2,  # BUY_LIMIT
            price_open=2495.0,
            price_current=2495.0,
            sl=2485.0,
            tp=2515.0,
            volume_initial=0.1,
            volume_current=0.1,
            state=1,
            magic=123456,
            comment="Test order 1"
        ),
        PendingOrder(
            ticket=54322,
            symbol="XAUUSD",
            type=3,  # SELL_LIMIT
            price_open=2515.0,
            price_current=2515.0,
            sl=2525.0,
            tp=2495.0,
            volume_initial=0.2,
            volume_current=0.2,
            state=1,
            magic=123457,
            comment="Test order 2"
        )
    ]


# Sample closed positions
@pytest.fixture
def sample_closed_positions():
    """Create sample closed positions."""
    return [
        ClosedPosition(
            ticket=11111,
            symbol="XAUUSD",
            volume=0.1,
            type=0,  # BUY
            price_open=2480.0,
            price_close=2490.0,
            profit=100.0,
            swap=0.0,
            commission=-2.0,
            comment="Closed position 1",
            magic=123456,
            time_open=datetime.now() - timedelta(hours=2),
            time_close=datetime.now() - timedelta(hours=1)
        ),
        ClosedPosition(
            ticket=11112,
            symbol="XAUUSD",
            volume=0.2,
            type=1,  # SELL
            price_open=2495.0,
            price_close=2500.0,
            profit=-100.0,
            swap=0.0,
            commission=-4.0,
            comment="Closed position 2",
            magic=123457,
            time_open=datetime.now() - timedelta(hours=3),
            time_close=datetime.now() - timedelta(hours=2)
        )
    ]


# Sample market state
@pytest.fixture
def sample_market_state(sample_positions, sample_pending_orders, sample_closed_positions):
    """Create a sample market state."""
    return MarketState(
        open_positions=sample_positions,
        pending_orders=sample_pending_orders,
        closed_positions=sample_closed_positions,
        timestamp=datetime.now()
    )


# Sample trading context
@pytest.fixture
def sample_trading_context(sample_market_state):
    """Create a sample trading context."""
    context = TradingContext()
    context.update_market_state(sample_market_state)
    return context


# Sample entry decisions
@pytest.fixture
def sample_entry_decision():
    """Create a sample entry decision."""
    return EntryDecision(
        symbol="XAUUSD",
        strategy_name="test_strategy",
        magic=123456,
        direction="long",
        entry_signals="BUY_LIMIT",
        entry_price=2495.0,
        position_size=0.1,
        stop_loss=StopLoss(level=2485.0, pips=100),
        take_profit=TakeProfit(level=2515.0, pips=200),
        decision_time=datetime.now()
    )


@pytest.fixture
def sample_entry_decisions():
    """Create sample entry decisions."""
    return [
        EntryDecision(
            symbol="XAUUSD",
            strategy_name="test_strategy",
            magic=123456,
            direction="long",
            entry_signals="BUY_LIMIT",
            entry_price=2495.0,
            position_size=0.1,
            stop_loss=StopLoss(level=2485.0, pips=100),
            take_profit=TakeProfit(level=2515.0, pips=200),
            decision_time=datetime.now()
        ),
        EntryDecision(
            symbol="XAUUSD",
            strategy_name="test_strategy",
            magic=123457,
            direction="short",
            entry_signals="SELL_LIMIT",
            entry_price=2515.0,
            position_size=0.2,
            stop_loss=StopLoss(level=2525.0, pips=100),
            take_profit=TakeProfit(level=2495.0, pips=200),
            decision_time=datetime.now()
        )
    ]


# Sample exit decisions
@pytest.fixture
def sample_exit_decision():
    """Create a sample exit decision."""
    return ExitDecision(
        symbol="XAUUSD",
        ticket=12345,
        reason="take_profit",
        exit_time=datetime.now()
    )


@pytest.fixture
def sample_exit_decisions():
    """Create sample exit decisions."""
    return [
        ExitDecision(
            symbol="XAUUSD",
            ticket=12345,
            reason="take_profit",
            exit_time=datetime.now()
        ),
        ExitDecision(
            symbol="XAUUSD",
            ticket=12346,
            reason="stop_loss",
            exit_time=datetime.now()
        )
    ]


# Sample trades
@pytest.fixture
def sample_trades(sample_entry_decisions, sample_exit_decisions):
    """Create sample trades."""
    return Trades(
        entries=sample_entry_decisions,
        exits=sample_exit_decisions
    )


# Sample suspended items
@pytest.fixture
def sample_suspended_order():
    """Create a sample suspended order item."""
    return {
        'ticket': 54321,
        'kind': 'pending_order',
        'original_sl': 2485.0,
        'original_tp': 2515.0,
        'symbol': 'XAUUSD',
        'order_type': 'BUY_LIMIT',
        'volume': 0.1,
        'price': 2495.0,
        'magic': 123456
    }


@pytest.fixture
def sample_suspended_position():
    """Create a sample suspended position item."""
    return {
        'ticket': 12345,
        'kind': 'position_sl_tp',
        'original_sl': 2490.0,
        'original_tp': 2520.0,
        'symbol': 'XAUUSD',
        'order_type': None,
        'volume': None,
        'price': None,
        'magic': 123456
    }


# Mock clients
@pytest.fixture
def mock_mt5_client():
    """Create a mock MT5 client."""
    client = Mock()
    
    # Mock positions API
    client.positions = Mock()
    client.positions.get_open_positions = Mock(return_value=[])
    client.positions.get_position_by_ticket = Mock(return_value=None)
    client.positions.close_position = Mock(return_value=True)
    client.positions.close_all_positions = Mock(return_value=True)
    client.positions.modify_position = Mock(return_value=True)
    
    # Mock orders API
    client.orders = Mock()
    client.orders.get_pending_orders = Mock(return_value=[])
    client.orders.create_buy_limit_order = Mock(return_value=True)
    client.orders.create_sell_limit_order = Mock(return_value=True)
    client.orders.create_buy_stop_order = Mock(return_value=True)
    client.orders.create_sell_stop_order = Mock(return_value=True)
    client.orders.delete_pending_order = Mock(return_value=True)
    
    # Mock history API
    client.history = Mock()
    client.history.get_closed_positions = Mock(return_value=[])
    
    return client


@pytest.fixture
def mock_live_trader(mock_mt5_client):
    """Create a mock live trader."""
    trader = Mock()
    trader.client = mock_mt5_client
    trader.get_open_positions = Mock(return_value=[])
    trader.get_pending_orders = Mock(return_value=[])
    trader.get_closed_positions = Mock(return_value=[])
    trader.close_open_position = Mock(return_value={"success": True})
    trader.close_all_open_position = Mock(return_value={"success": True})
    trader.update_open_position = Mock(return_value={"success": True})
    trader.cancel_pending_orders = Mock(return_value={"success": True})
    trader.cancel_all_pending_orders = Mock(return_value=[{"success": True}])
    trader.execute_orders = Mock(return_value=[])
    return trader


# Mock components
@pytest.fixture
def mock_exit_manager():
    """Create a mock exit manager."""
    manager = Mock()
    manager.process_exits = Mock()
    return manager


@pytest.fixture
def mock_duplicate_filter():
    """Create a mock duplicate filter."""
    filter = Mock()
    filter.filter_entries = Mock(return_value=[])
    return filter


@pytest.fixture
def mock_risk_monitor():
    """Create a mock risk monitor."""
    monitor = Mock()
    monitor.check_catastrophic_loss_limit = Mock(return_value=False)
    monitor.get_risk_metrics = Mock(return_value={
        'daily_pnl': 0.0,
        'floating_pnl': 0.0,
        'total_pnl': 0.0
    })
    return monitor


@pytest.fixture
def mock_order_executor():
    """Create a mock order executor."""
    executor = Mock()
    executor.execute_entries = Mock()
    return executor


@pytest.fixture
def mock_restriction_manager():
    """Create a mock restriction manager."""
    manager = Mock()
    manager.apply_restrictions = Mock()
    manager.check_news_restriction = Mock(return_value=False)
    manager.check_market_closing = Mock(return_value=False)
    return manager


@pytest.fixture
def mock_suspension_store():
    """Create a mock suspension store."""
    store = Mock(spec=SuspensionStore)
    store.add = Mock()
    store.all = Mock(return_value=[])
    store.get_by_kind = Mock(return_value=[])
    store.clear = Mock()
    store.is_empty = Mock(return_value=True)
    store.count = Mock(return_value=0)
    store.get_summary = Mock(return_value={
        'total': 0,
        'pending_order': 0,
        'position_sl_tp': 0
    })
    return store


@pytest.fixture
def mock_date_helper():
    """Create a mock date helper."""
    helper = Mock()
    helper.get_date_days_ago = Mock(side_effect=lambda x: 
        (datetime.now() - timedelta(days=abs(x))).strftime("%Y-%m-%d")
    )
    helper.now = Mock(return_value=datetime.now())
    return helper


@pytest.fixture
def mock_logger():
    """Create a mock logger."""
    logger = Mock()
    logger.info = Mock()
    logger.debug = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    return logger