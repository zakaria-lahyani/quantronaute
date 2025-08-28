"""
Integration tests for TradeExecutor (v2).
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.trader.trade_executor import TradeExecutor
from app.strategy_builder.data.dtos import Trades, EntryDecision, ExitDecision
from app.utils.date_helper import DateHelper
from app.utils.config import LoadEnvironmentVariables


class TestTradeExecutorIntegration:
    """Integration tests for the refactored TradeExecutor."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing."""
        config = Mock(spec=LoadEnvironmentVariables)
        config.POSITION_SPLIT = 2
        config.SCALING_TYPE = "linear"
        config.ENTRY_SPACING = 10.0
        config.RISK_PER_GROUP = 2.0
        config.SYMBOL = "XAUUSD"
        config.DAILY_LOSS_LIMIT = -1000.0
        return config
    
    @pytest.fixture
    def mock_client(self):
        """Mock MT5 client for testing."""
        return Mock()
    
    @pytest.fixture
    def mock_date_helper(self):
        """Mock date helper for testing."""
        date_helper = Mock(spec=DateHelper)
        date_helper.get_date_days_ago.side_effect = lambda n: f"2025-01-{15+n:02d}"
        return date_helper
    
    @pytest.fixture
    def sample_trades(self):
        """Sample trades for testing."""
        entries = [
            EntryDecision(
                symbol="XAUUSD",
                strategy_name="test-strategy",
                magic=123456789,
                direction="long",
                entry_signals="BUY_LIMIT",
                entry_price=3380.0,
                position_size=0.1,
                stop_loss=Mock(),
                take_profit=Mock(),
                decision_time=datetime.now()
            )
        ]
        
        exits = [
            ExitDecision(
                symbol="XAUUSD",
                strategy_name="test-strategy",
                magic=123456789,
                direction="long",
                decision_time=datetime.now()
            )
        ]
        
        return Trades(entries=entries, exits=exits)
    
    def test_init_live_mode_success(self, mock_config, mock_client):
        """Test successful initialization in live mode."""
        executor = TradeExecutor("live", mock_config, client=mock_client)
        
        assert executor.mode == "live"
        assert executor.config == mock_config
        assert executor.exit_manager is not None
        assert executor.duplicate_filter is not None
        assert executor.pnl_calculator is not None
        assert executor.risk_monitor is not None
        assert executor.order_executor is not None
        assert executor.trader is not None
    
    def test_init_live_mode_missing_client(self, mock_config):
        """Test initialization failure when client is missing in live mode."""
        with pytest.raises(ValueError, match="Live trading requires client"):
            TradeExecutor("live", mock_config)
    
    def test_init_unsupported_mode(self, mock_config, mock_client):
        """Test initialization failure with unsupported mode."""
        with pytest.raises(ValueError, match="Unsupported mode: backtest"):
            TradeExecutor("backtest", mock_config, client=mock_client)
    
    @patch('app.trader.live_trader.LiveTrader')
    def test_manage_full_cycle_success(self, mock_live_trader_class, mock_config, mock_client, mock_date_helper, sample_trades):
        """Test full manage cycle with successful execution."""
        # Set up mock trader instance
        mock_trader_instance = Mock()
        mock_live_trader_class.return_value = mock_trader_instance
        
        # Configure trader responses
        mock_trader_instance.get_closed_positions.return_value = []
        mock_trader_instance.get_pending_orders.return_value = []
        mock_trader_instance.get_open_positions.return_value = []
        mock_trader_instance.get_current_price.return_value = 3400.0
        
        # Create executor
        executor = TradeExecutor("live", mock_config, client=mock_client)
        
        # Mock the risk calculator to avoid complex setup
        executor.order_executor.risk_calculator.process_entries.return_value = []
        
        # Execute manage cycle
        executor.manage(sample_trades, mock_date_helper)
        
        # Verify data fetching calls
        mock_trader_instance.get_closed_positions.assert_called_once_with("2025-01-15T00:00:00Z", "2025-01-16T00:00:00Z")
        mock_trader_instance.get_pending_orders.assert_called_once_with("XAUUSD")
        mock_trader_instance.get_open_positions.assert_called_once_with("XAUUSD")
    
    @patch('app.trader.live_trader.LiveTrader')
    def test_manage_with_risk_breach(self, mock_live_trader_class, mock_config, mock_client, mock_date_helper, sample_trades):
        """Test manage cycle when risk limit is breached."""
        mock_trader_instance = Mock()
        mock_live_trader_class.return_value = mock_trader_instance
        
        # Configure trader to return data that would breach risk limits
        from app.clients.mt5.models.response import Position
        
        losing_position = Position(
            ticket=12345, symbol="XAUUSD", type=0, magic=123,
            profit=-2000.0, swap=-50.0, volume=1.0,  # Large loss
            price_open=3400.0, price_current=3200.0,
            sl=3100.0, tp=3500.0, time=123456, comment=""
        )
        
        mock_trader_instance.get_closed_positions.return_value = []
        mock_trader_instance.get_pending_orders.return_value = []
        mock_trader_instance.get_open_positions.return_value = [losing_position]
        
        executor = TradeExecutor("live", mock_config, client=mock_client)
        
        # Execute manage cycle
        executor.manage(sample_trades, mock_date_helper)
        
        # Should trigger emergency shutdown
        mock_trader_instance.close_all_open_position.assert_called_once()
        mock_trader_instance.cancel_all_pending_orders.assert_called_once()
    
    @patch('app.trader.live_trader.LiveTrader')
    def test_manage_with_duplicate_entries(self, mock_live_trader_class, mock_config, mock_client, mock_date_helper):
        """Test manage cycle with duplicate entries."""
        mock_trader_instance = Mock()
        mock_live_trader_class.return_value = mock_trader_instance
        
        # Set up pending order that matches entry
        from app.clients.mt5.models.order import PendingOrder
        
        existing_order = PendingOrder(
            ticket=54321, symbol="XAUUSD", type=2, magic=123456789,  # BUY_LIMIT with same magic
            price_open=3380.0, price_current=3400.0,
            sl=3370.0, tp=3400.0, volume_initial=0.1, volume_current=0.1,
            state=1, comment=""
        )
        
        mock_trader_instance.get_closed_positions.return_value = []
        mock_trader_instance.get_pending_orders.return_value = [existing_order]
        mock_trader_instance.get_open_positions.return_value = []
        
        # Create entry that duplicates the existing order
        duplicate_entry = EntryDecision(
            symbol="XAUUSD", strategy_name="test", magic=123456789,
            direction="long", entry_signals="BUY_LIMIT", entry_price=3380.0,
            position_size=0.1, stop_loss=Mock(), take_profit=Mock(),
            decision_time=datetime.now()
        )
        
        trades = Trades(entries=[duplicate_entry], exits=[])
        executor = TradeExecutor("live", mock_config, client=mock_client)
        
        # Execute manage cycle
        executor.manage(trades, mock_date_helper)
        
        # Should not call get_current_price (no entries to execute after filtering)
        mock_trader_instance.get_current_price.assert_not_called()
    
    @patch('app.trader.live_trader.LiveTrader')
    def test_manage_exception_handling(self, mock_live_trader_class, mock_config, mock_client, mock_date_helper, sample_trades):
        """Test exception handling during manage cycle."""
        mock_trader_instance = Mock()
        mock_live_trader_class.return_value = mock_trader_instance
        
        # Make data fetching raise an exception
        mock_trader_instance.get_closed_positions.side_effect = Exception("Data fetch failed")
        
        executor = TradeExecutor("live", mock_config, client=mock_client)
        
        # Should not raise exception
        executor.manage(sample_trades, mock_date_helper)
        
        # Should log error (we can't easily assert this without logger mocking)
    
    @patch('app.trader.live_trader.LiveTrader')
    def test_get_risk_metrics(self, mock_live_trader_class, mock_config, mock_client, mock_date_helper):
        """Test getting risk metrics."""
        mock_trader_instance = Mock()
        mock_live_trader_class.return_value = mock_trader_instance
        
        # Configure trader responses
        mock_trader_instance.get_closed_positions.return_value = []
        mock_trader_instance.get_pending_orders.return_value = []
        mock_trader_instance.get_open_positions.return_value = []
        
        executor = TradeExecutor("live", mock_config, client=mock_client)
        
        metrics = executor.get_risk_metrics(mock_date_helper)
        
        # Should return risk metrics dictionary
        assert isinstance(metrics, dict)
        assert 'total_daily_pnl' in metrics
        assert 'daily_loss_limit' in metrics
        assert 'loss_ratio' in metrics
        assert 'open_positions_count' in metrics
        assert 'floating_pnl' in metrics
        assert 'closed_pnl' in metrics
    
    @patch('app.trader.live_trader.LiveTrader')
    def test_component_integration(self, mock_live_trader_class, mock_config, mock_client, mock_date_helper):
        """Test that all components are properly integrated."""
        mock_trader_instance = Mock()
        mock_live_trader_class.return_value = mock_trader_instance
        
        # Configure minimal responses
        mock_trader_instance.get_closed_positions.return_value = []
        mock_trader_instance.get_pending_orders.return_value = []
        mock_trader_instance.get_open_positions.return_value = []
        
        executor = TradeExecutor("live", mock_config, client=mock_client)
        
        # Verify all components are initialized with correct dependencies
        assert executor.exit_manager.trader == mock_trader_instance
        assert executor.risk_monitor.trader == mock_trader_instance
        assert executor.risk_monitor.daily_loss_limit == -1000.0
        assert executor.order_executor.trader == mock_trader_instance
        assert executor.order_executor.symbol == "XAUUSD"
        
        # Verify shared components
        assert executor.risk_monitor.pnl_calculator == executor.pnl_calculator
    
    @patch('app.trader.live_trader.LiveTrader')
    def test_orchestration_flow(self, mock_live_trader_class, mock_config, mock_client, mock_date_helper, sample_trades):
        """Test the orchestration flow of manage method."""
        mock_trader_instance = Mock()
        mock_live_trader_class.return_value = mock_trader_instance
        
        # Configure responses
        mock_trader_instance.get_closed_positions.return_value = []
        mock_trader_instance.get_pending_orders.return_value = []
        mock_trader_instance.get_open_positions.return_value = []
        mock_trader_instance.get_current_price.return_value = 3400.0
        
        executor = TradeExecutor("live", mock_config, client=mock_client)
        
        # Mock component methods to track calls
        executor.exit_manager.process_exits = Mock()
        executor.risk_monitor.check_catastrophic_loss_limit = Mock(return_value=False)
        executor.duplicate_filter.filter_entries = Mock(return_value=sample_trades.entries)
        executor.order_executor.execute_entries = Mock()
        
        # Execute manage cycle
        executor.manage(sample_trades, mock_date_helper)
        
        # Verify orchestration sequence
        executor.exit_manager.process_exits.assert_called_once()
        executor.risk_monitor.check_catastrophic_loss_limit.assert_called_once()
        executor.duplicate_filter.filter_entries.assert_called_once()
        executor.order_executor.execute_entries.assert_called_once()
    
    @patch('app.trader.live_trader.LiveTrader')
    def test_configuration_propagation(self, mock_live_trader_class, mock_config, mock_client):
        """Test that configuration is properly propagated to components."""
        mock_trader_instance = Mock()
        mock_live_trader_class.return_value = mock_trader_instance
        
        # Modify config values
        mock_config.POSITION_SPLIT = 3
        mock_config.SCALING_TYPE = "exponential"
        mock_config.SYMBOL = "EURUSD"
        mock_config.DAILY_LOSS_LIMIT = -500.0
        
        executor = TradeExecutor("live", mock_config, client=mock_client)
        
        # Verify configuration propagation
        assert executor.risk_monitor.daily_loss_limit == -500.0
        assert executor.order_executor.symbol == "EURUSD"
        
        # Note: We can't easily test ScalingConfig propagation without more complex mocking
        # but the initialization would fail if config wasn't passed correctly
    
    @patch('app.trader.live_trader.LiveTrader')
    def test_empty_trades_handling(self, mock_live_trader_class, mock_config, mock_client, mock_date_helper):
        """Test handling of empty trades."""
        mock_trader_instance = Mock()
        mock_live_trader_class.return_value = mock_trader_instance
        
        # Configure responses
        mock_trader_instance.get_closed_positions.return_value = []
        mock_trader_instance.get_pending_orders.return_value = []
        mock_trader_instance.get_open_positions.return_value = []
        
        executor = TradeExecutor("live", mock_config, client=mock_client)
        
        # Mock component methods
        executor.exit_manager.process_exits = Mock()
        executor.order_executor.execute_entries = Mock()
        
        # Execute with empty trades
        empty_trades = Trades(entries=[], exits=[])
        executor.manage(empty_trades, mock_date_helper)
        
        # Should still call components but with empty lists
        executor.exit_manager.process_exits.assert_called_once_with([], [])
        executor.order_executor.execute_entries.assert_called_once_with([])
    
    def test_trade_executor_as_drop_in_replacement(self, mock_config, mock_client):
        """Test that TradeExecutor v2 can be used as drop-in replacement."""
        # This test verifies the interface compatibility
        
        executor = TradeExecutor("live", mock_config, client=mock_client)
        
        # Should have the same public interface as original
        assert hasattr(executor, 'manage')
        assert hasattr(executor, 'get_risk_metrics')  # New method, bonus
        
        # manage method should accept the same parameters
        import inspect
        manage_signature = inspect.signature(executor.manage)
        expected_params = ['trades', 'date_helper']
        actual_params = list(manage_signature.parameters.keys())[1:]  # Skip 'self'
        
        assert actual_params == expected_params