"""Unit tests for TradeExecutor class."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from app.trader.trade_executor import TradeExecutor
from app.trader.trading_context import TradingContext, MarketState
from app.strategy_builder.data.dtos import Trades
from .fixtures import *


class TestTradeExecutor:
    """Test cases for TradeExecutor class."""

    @pytest.fixture
    def trade_executor(self, mock_live_trader, mock_exit_manager, mock_duplicate_filter,
                      mock_risk_monitor, mock_order_executor, mock_restriction_manager):
        """Create a TradeExecutor instance for testing."""
        return TradeExecutor(
            trader=mock_live_trader,
            exit_manager=mock_exit_manager,
            duplicate_filter=mock_duplicate_filter,
            risk_monitor=mock_risk_monitor,
            order_executor=mock_order_executor,
            restriction_manager=mock_restriction_manager,
            symbol="XAUUSD"
        )

    def test_init(self, trade_executor):
        """Test TradeExecutor initialization."""
        assert trade_executor.symbol == "XAUUSD"
        assert trade_executor.trader is not None
        assert trade_executor.exit_manager is not None
        assert trade_executor.duplicate_filter is not None
        assert trade_executor.risk_monitor is not None
        assert trade_executor.order_executor is not None
        assert trade_executor.restriction_manager is not None
        assert trade_executor.logger is not None
        assert isinstance(trade_executor.context, TradingContext)

    def test_execute_trading_cycle_full_flow(self, trade_executor, sample_trades, 
                                           mock_date_helper, sample_positions,
                                           sample_pending_orders, sample_closed_positions):
        """Test complete trading cycle execution."""
        # Mock market data
        trade_executor.trader.get_open_positions.return_value = sample_positions
        trade_executor.trader.get_pending_orders.return_value = sample_pending_orders
        trade_executor.trader.get_closed_positions.return_value = sample_closed_positions
        
        # Mock components to not block trading
        trade_executor.restriction_manager.apply_restrictions.return_value = None
        trade_executor.risk_monitor.check_catastrophic_loss_limit.return_value = False
        trade_executor.duplicate_filter.filter_entries.return_value = sample_trades.entries
        
        # Execute trading cycle
        context = trade_executor.execute_trading_cycle(sample_trades, mock_date_helper)
        
        # Verify all components were called
        trade_executor.restriction_manager.apply_restrictions.assert_called_once()
        trade_executor.exit_manager.process_exits.assert_called_once()
        trade_executor.risk_monitor.check_catastrophic_loss_limit.assert_called_once()
        trade_executor.duplicate_filter.filter_entries.assert_called_once()
        trade_executor.order_executor.execute_entries.assert_called_once()
        
        assert isinstance(context, TradingContext)

    def test_execute_trading_cycle_no_exits(self, trade_executor, mock_date_helper):
        """Test trading cycle with no exit signals."""
        trades = Trades(entries=[], exits=[])
        
        context = trade_executor.execute_trading_cycle(trades, mock_date_helper)
        
        # Exit manager should not be called for processing
        trade_executor.exit_manager.process_exits.assert_not_called()

    def test_execute_trading_cycle_no_entries(self, trade_executor, mock_date_helper):
        """Test trading cycle with no entry signals."""
        trades = Trades(entries=[], exits=[])
        
        context = trade_executor.execute_trading_cycle(trades, mock_date_helper)
        
        # Order executor should not be called
        trade_executor.order_executor.execute_entries.assert_not_called()

    def test_execute_trading_cycle_trading_blocked_by_restrictions(self, trade_executor, 
                                                                  sample_trades, mock_date_helper):
        """Test trading cycle when blocked by restrictions."""
        # Mock restriction manager to block trading
        trade_executor.context.block_trading("news restriction")
        
        context = trade_executor.execute_trading_cycle(sample_trades, mock_date_helper)
        
        # Order executor should not be called when trading is blocked
        trade_executor.order_executor.execute_entries.assert_not_called()

    def test_execute_trading_cycle_trading_blocked_by_risk(self, trade_executor, 
                                                          sample_trades, mock_date_helper):
        """Test trading cycle when blocked by risk breach."""
        # Mock risk monitor to return risk breach
        trade_executor.risk_monitor.check_catastrophic_loss_limit.return_value = True
        
        context = trade_executor.execute_trading_cycle(sample_trades, mock_date_helper)
        
        # Order executor should not be called when risk is breached
        trade_executor.order_executor.execute_entries.assert_not_called()
        assert context.risk_breached

    def test_execute_trading_cycle_all_entries_filtered(self, trade_executor, 
                                                       sample_trades, mock_date_helper):
        """Test trading cycle when all entries are filtered out."""
        # Mock duplicate filter to filter out all entries
        trade_executor.duplicate_filter.filter_entries.return_value = []
        
        context = trade_executor.execute_trading_cycle(sample_trades, mock_date_helper)
        
        # Order executor should not be called when all entries are filtered
        trade_executor.order_executor.execute_entries.assert_not_called()

    def test_execute_trading_cycle_exception_handling(self, trade_executor, 
                                                     sample_trades, mock_date_helper):
        """Test trading cycle exception handling."""
        # Mock an exception in one of the components
        trade_executor.exit_manager.process_exits.side_effect = Exception("Exit error")
        
        context = trade_executor.execute_trading_cycle(sample_trades, mock_date_helper)
        
        # Context should be blocked due to error
        assert not context.can_trade()

    def test_update_context(self, trade_executor, mock_date_helper, 
                           sample_positions, sample_pending_orders, sample_closed_positions):
        """Test context update."""
        # Mock market data
        trade_executor.trader.get_open_positions.return_value = sample_positions
        trade_executor.trader.get_pending_orders.return_value = sample_pending_orders
        trade_executor.trader.get_closed_positions.return_value = sample_closed_positions
        
        trade_executor._update_context(mock_date_helper)
        
        assert trade_executor.context.current_time is not None
        assert trade_executor.context.market_state is not None
        assert len(trade_executor.context.market_state.open_positions) == len(sample_positions)

    def test_fetch_market_state(self, trade_executor, mock_date_helper,
                               sample_positions, sample_pending_orders, sample_closed_positions):
        """Test market state fetching."""
        # Mock market data
        trade_executor.trader.get_open_positions.return_value = sample_positions
        trade_executor.trader.get_pending_orders.return_value = sample_pending_orders
        trade_executor.trader.get_closed_positions.return_value = sample_closed_positions
        
        market_state = trade_executor._fetch_market_state(mock_date_helper)
        
        assert isinstance(market_state, MarketState)
        assert len(market_state.open_positions) == len(sample_positions)
        assert len(market_state.pending_orders) == len(sample_pending_orders)
        assert len(market_state.closed_positions) == len(sample_closed_positions)
        
        # Verify API calls
        trade_executor.trader.get_open_positions.assert_called_with("XAUUSD")
        trade_executor.trader.get_pending_orders.assert_called_with("XAUUSD")
        trade_executor.trader.get_closed_positions.assert_called_once()

    def test_apply_restrictions(self, trade_executor):
        """Test restriction application."""
        trade_executor._apply_restrictions()
        
        trade_executor.restriction_manager.apply_restrictions.assert_called_once_with(
            trade_executor.context
        )

    def test_process_exits_with_signals(self, trade_executor, sample_trades, sample_positions):
        """Test exit processing with signals."""
        trade_executor.context.market_state = Mock()
        trade_executor.context.market_state.open_positions = sample_positions
        
        trade_executor._process_exits(sample_trades)
        
        trade_executor.exit_manager.process_exits.assert_called_once_with(
            sample_trades.exits, sample_positions
        )

    def test_process_exits_no_signals(self, trade_executor):
        """Test exit processing without signals."""
        trades = Trades(entries=[], exits=[])
        
        trade_executor._process_exits(trades)
        
        trade_executor.exit_manager.process_exits.assert_not_called()

    def test_check_risk_limits_normal(self, trade_executor, sample_positions, sample_closed_positions):
        """Test risk limit checking under normal conditions."""
        # Mock risk monitor
        trade_executor.risk_monitor.check_catastrophic_loss_limit.return_value = False
        trade_executor.risk_monitor.get_risk_metrics.return_value = {
            'daily_pnl': 100.0,
            'floating_pnl': 50.0,
            'total_pnl': 150.0
        }
        
        # Set up context
        trade_executor.context.market_state = Mock()
        trade_executor.context.market_state.open_positions = sample_positions
        trade_executor.context.market_state.closed_positions = sample_closed_positions
        
        trade_executor._check_risk_limits()
        
        assert not trade_executor.context.risk_breached
        assert trade_executor.context.daily_pnl == 100.0
        assert trade_executor.context.floating_pnl == 50.0
        assert trade_executor.context.total_pnl == 150.0

    def test_check_risk_limits_breach(self, trade_executor, sample_positions, sample_closed_positions):
        """Test risk limit checking with breach."""
        # Mock risk monitor to return breach
        trade_executor.risk_monitor.check_catastrophic_loss_limit.return_value = True
        trade_executor.risk_monitor.get_risk_metrics.return_value = {
            'daily_pnl': -5000.0,
            'floating_pnl': -1000.0,
            'total_pnl': -6000.0
        }
        
        # Set up context
        trade_executor.context.market_state = Mock()
        trade_executor.context.market_state.open_positions = sample_positions
        trade_executor.context.market_state.closed_positions = sample_closed_positions
        
        trade_executor._check_risk_limits()
        
        assert trade_executor.context.risk_breached
        assert trade_executor.context.daily_pnl == -5000.0
        assert trade_executor.context.floating_pnl == -1000.0
        assert trade_executor.context.total_pnl == -6000.0

    def test_process_entries_authorized(self, trade_executor, sample_trades, 
                                       sample_positions, sample_pending_orders):
        """Test entry processing when authorized."""
        # Set up context to allow trading
        trade_executor.context.trade_authorized = True
        trade_executor.context.risk_breached = False
        trade_executor.context.market_state = Mock()
        trade_executor.context.market_state.open_positions = sample_positions
        trade_executor.context.market_state.pending_orders = sample_pending_orders
        
        # Mock duplicate filter to return filtered entries
        filtered_entries = [sample_trades.entries[0]]
        trade_executor.duplicate_filter.filter_entries.return_value = filtered_entries
        
        trade_executor._process_entries(sample_trades)
        
        trade_executor.duplicate_filter.filter_entries.assert_called_once_with(
            sample_trades.entries, sample_positions, sample_pending_orders
        )
        trade_executor.order_executor.execute_entries.assert_called_once_with(filtered_entries)

    def test_process_entries_not_authorized(self, trade_executor, sample_trades):
        """Test entry processing when not authorized."""
        # Set up context to block trading
        trade_executor.context.trade_authorized = False
        trade_executor.context.risk_breached = False
        
        trade_executor._process_entries(sample_trades)
        
        # Should not execute any orders
        trade_executor.order_executor.execute_entries.assert_not_called()

    def test_process_entries_risk_breach(self, trade_executor, sample_trades):
        """Test entry processing with risk breach."""
        # Set up context with risk breach
        trade_executor.context.trade_authorized = True
        trade_executor.context.risk_breached = True
        
        trade_executor._process_entries(sample_trades)
        
        # Should not execute any orders
        trade_executor.order_executor.execute_entries.assert_not_called()

    def test_process_entries_both_blocks(self, trade_executor, sample_trades):
        """Test entry processing with both authorization and risk blocks."""
        # Set up context with both blocks
        trade_executor.context.trade_authorized = False
        trade_executor.context.risk_breached = True
        
        trade_executor._process_entries(sample_trades)
        
        # Should not execute any orders
        trade_executor.order_executor.execute_entries.assert_not_called()

    def test_process_entries_no_entries_after_filter(self, trade_executor, sample_trades,
                                                    sample_positions, sample_pending_orders):
        """Test entry processing when all entries are filtered out."""
        # Set up context to allow trading
        trade_executor.context.trade_authorized = True
        trade_executor.context.risk_breached = False
        trade_executor.context.market_state = Mock()
        trade_executor.context.market_state.open_positions = sample_positions
        trade_executor.context.market_state.pending_orders = sample_pending_orders
        
        # Mock duplicate filter to filter out all entries
        trade_executor.duplicate_filter.filter_entries.return_value = []
        
        trade_executor._process_entries(sample_trades)
        
        # Should not execute any orders
        trade_executor.order_executor.execute_entries.assert_not_called()

    def test_get_context(self, trade_executor):
        """Test getting trading context."""
        context = trade_executor.get_context()
        
        assert isinstance(context, TradingContext)
        assert context is trade_executor.context

    @patch('app.trader.trade_executor.datetime')
    def test_context_time_update(self, mock_datetime, trade_executor, mock_date_helper):
        """Test that context time is updated correctly."""
        fixed_time = datetime(2024, 1, 15, 10, 30, 0)
        mock_datetime.now.return_value = fixed_time
        
        trade_executor._update_context(mock_date_helper)
        
        assert trade_executor.context.current_time == fixed_time

    def test_market_state_integration(self, trade_executor, mock_date_helper):
        """Test market state integration with real data flow."""
        # Create realistic market data
        positions = [Mock(ticket=123, symbol="XAUUSD", volume=0.1)]
        orders = [Mock(ticket=456, symbol="XAUUSD", volume_current=0.2)]
        closed = [Mock(ticket=789, symbol="XAUUSD", profit=100.0)]
        
        trade_executor.trader.get_open_positions.return_value = positions
        trade_executor.trader.get_pending_orders.return_value = orders
        trade_executor.trader.get_closed_positions.return_value = closed
        
        # Execute update
        trade_executor._update_context(mock_date_helper)
        
        # Verify market state is properly set
        market_state = trade_executor.context.market_state
        assert market_state is not None
        assert len(market_state.open_positions) == 1
        assert len(market_state.pending_orders) == 1
        assert len(market_state.closed_positions) == 1