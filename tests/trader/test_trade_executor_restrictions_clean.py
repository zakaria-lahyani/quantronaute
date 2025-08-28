"""
Unit tests for TradeExecutor trading restrictions functionality.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, call

from app.trader.trade_executor import TradeExecutor
from app.strategy_builder.data.dtos import Trades, EntryDecision, ExitDecision
from app.utils.config import LoadEnvironmentVariables
from app.utils.date_helper import DateHelper


class TestTradeExecutorRestrictions:
    """Test cases for trading restrictions in TradeExecutor."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        config = Mock(spec=LoadEnvironmentVariables)
        config.POSITION_SPLIT = 3
        config.SCALING_TYPE = "linear"
        config.ENTRY_SPACING = 10.0
        config.RISK_PER_GROUP = 100.0
        config.SYMBOL = "XAUUSD"
        config.ACCOUNT_TYPE = "daily"
        config.DAILY_LOSS_LIMIT = 500.0
        config.RESTRICTION_CONF_FOLDER_PATH = "/config"
        config.DEFAULT_CLOSE_TIME = "16:00"
        config.NEWS_RESTRICTION_DURATION = 30
        config.MARKET_CLOSE_RESTRICTION_DURATION = 60
        return config
    
    @pytest.fixture
    def mock_client(self):
        """Mock MT5 client."""
        return Mock()
    
    @pytest.fixture
    def mock_date_helper(self):
        """Mock date helper."""
        helper = Mock()
        helper.now.return_value = datetime(2025, 1, 15, 12, 0, 0)
        helper.get_date_days_ago.side_effect = lambda days: f"2025-01-{15-days}"
        return helper
    
    @pytest.fixture
    def trade_executor(self, mock_config, mock_client):
        """Create TradeExecutor instance for testing."""
        with patch('app.trader.trade_executor.LiveTrader') as mock_trader_class:
            with patch('app.trader.trade_executor.RiskCalculator'), \
                 patch('app.trader.trade_executor.TradeRestriction') as mock_restriction_class:
                
                mock_trader = Mock()
                mock_trader_class.return_value = mock_trader
                
                mock_restriction = Mock()
                mock_restriction_class.return_value = mock_restriction
                
                executor = TradeExecutor('live', mock_config, client=mock_client)
                executor.trader = mock_trader
                executor.trade_restriction = mock_restriction
                
                # Setup default trader responses
                mock_trader.get_closed_positions.return_value = []
                mock_trader.get_pending_orders.return_value = []
                mock_trader.get_open_positions.return_value = []
                mock_trader.cancel_pending_orders.return_value = {'status': 'success'}
                mock_trader.update_open_position.return_value = {'status': 'success'}
                mock_trader.close_open_position.return_value = {'status': 'success'}
                
                return executor
    
    def test_news_event_suspension_activation(self, trade_executor, mock_date_helper):
        """Test news event triggers suspension of trading activity."""
        # Setup: news event becomes active, market not closing
        trade_executor.trade_restriction.is_news_block_active.return_value = True
        trade_executor.trade_restriction.is_market_closing_soon.return_value = False
        trade_executor.last_news_state = False  # Transition from False to True
        
        # Create mock pending orders and positions
        pending_orders = [
            Mock(ticket=12345, symbol="XAUUSD", sl=1.1000, tp=1.1200, 
                 type=2, volume_current=0.1, price_open=1.1050, magic=123456)
        ]
        
        positions = [
            Mock(ticket=67890, symbol="XAUUSD", sl=1.1000, tp=1.1200, magic=123456)
        ]
        
        market_state = {
            'pending_orders': pending_orders,
            'open_positions': positions,
            'closed_positions': []
        }
        
        # Execute
        trade_executor._apply_trading_restrictions(mock_date_helper.now(), market_state)
        
        # Verify suspension occurred
        assert not trade_executor.trade_authorized
        assert trade_executor.last_news_state == True
        assert trade_executor.suspension_store.count() == 2  # 1 order + 1 position SL/TP
        
        # Verify trader methods were called
        trade_executor.trader.cancel_pending_orders.assert_called_once_with(12345)
        trade_executor.trader.update_open_position.assert_called_once_with("XAUUSD", 67890, None, None)
    
    def test_news_event_suspension_restoration(self, trade_executor, mock_date_helper):
        """Test news event ending triggers restoration of suspended items."""
        # Setup: Add items to suspension store
        from app.trader.suspension_store import SuspendedItem
        
        pending_item: SuspendedItem = {
            'ticket': 12345,
            'kind': 'pending_order',
            'original_sl': 1.1000,
            'original_tp': 1.1200,
            'symbol': 'XAUUSD',
            'order_type': 'BUY_LIMIT',
            'volume': 0.1,
            'price': 1.1050,
            'magic': 123456
        }
        
        position_item: SuspendedItem = {
            'ticket': 67890,
            'kind': 'position_sl_tp',
            'original_sl': 1.1000,
            'original_tp': 1.1200,
            'symbol': 'XAUUSD',
            'order_type': None,
            'volume': None,
            'price': None,
            'magic': 123456
        }
        
        trade_executor.suspension_store.add(pending_item)
        trade_executor.suspension_store.add(position_item)
        
        # Setup: news event ends, market not closing
        trade_executor.trade_restriction.is_news_block_active.return_value = False
        trade_executor.trade_restriction.is_market_closing_soon.return_value = False
        trade_executor.last_news_state = True  # Transition from True to False
        trade_executor.trade_authorized = False
        
        market_state = {
            'pending_orders': [],
            'open_positions': [],
            'closed_positions': []
        }
        
        # Execute
        trade_executor._apply_trading_restrictions(mock_date_helper.now(), market_state)
        
        # Verify restoration occurred
        assert trade_executor.trade_authorized
        assert trade_executor.last_news_state == False
        assert trade_executor.suspension_store.is_empty()
        
        # Verify SL/TP restoration was attempted
        trade_executor.trader.update_open_position.assert_called_with(
            'XAUUSD', 67890, 1.1000, 1.1200
        )
    
    def test_suspension_store_initialization(self, trade_executor, mock_date_helper):
        """Test that suspension store is properly initialized."""
        assert trade_executor.suspension_store is not None
        assert trade_executor.suspension_store.is_empty()
        assert trade_executor.last_news_state is None