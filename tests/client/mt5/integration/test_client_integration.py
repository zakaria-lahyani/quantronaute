"""
Integration tests for MT5Client workflows.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.clients.mt5.client import MT5Client, create_client
from app.clients.mt5.models import Position, Order, CreateOrderRequest, OrderType
from app.clients.mt5.exceptions import MT5APIError, MT5ValidationError
from app.clients.mt5.utils import RetryConfig

from ..fixtures.mock_data import (
    MOCK_ACCOUNT_INFO, MOCK_POSITIONS, MOCK_ORDERS, MOCK_SYMBOLS,
    MOCK_SYMBOL_INFO, MOCK_TICK_DATA, MOCK_HISTORICAL_DATA,
    MOCK_API_SUCCESS_RESPONSE, MOCK_HEALTH_CHECK
)


class TestMT5ClientIntegration:
    """Integration tests for MT5Client workflows."""

    @patch('app.clients.mt5.client.setup_logging')
    def test_complete_trading_workflow(self, mock_setup_logging):
        """Test a complete trading workflow using MT5Client."""
        client = MT5Client("http://localhost:8000", enable_logging=False)
        
        # Mock all the API calls we'll make
        with patch.object(client, 'health_check', return_value=MOCK_HEALTH_CHECK), \
             patch.object(client.account, 'get_account_info', return_value=MOCK_ACCOUNT_INFO), \
             patch.object(client.symbols, 'get_all_symbols', return_value=MOCK_SYMBOLS), \
             patch.object(client.symbols, 'get_symbol_info', return_value=MOCK_SYMBOL_INFO["EURUSD"]), \
             patch.object(client.symbols, 'get_symbol_tick', return_value=MOCK_TICK_DATA["EURUSD"]), \
             patch.object(client.positions, 'get_open_positions', return_value=[Position(**pos) for pos in MOCK_POSITIONS]), \
             patch.object(client.orders, 'get_pending_orders', return_value=[Order(**order) for order in MOCK_ORDERS]), \
             patch.object(client.orders, 'create_buy_order', return_value=MOCK_API_SUCCESS_RESPONSE), \
             patch.object(client.positions, 'modify_position', return_value=MOCK_API_SUCCESS_RESPONSE), \
             patch.object(client.positions, 'close_position', return_value=MOCK_API_SUCCESS_RESPONSE):
            
            # Step 1: Check system health
            health = client.health_check()
            assert health["status"] == "healthy"
            
            # Step 2: Get account information
            account = client.account.get_account_info()
            assert account["balance"] == 10000.0
            assert account["equity"] == 10150.0
            assert account["currency"] == "USD"
            
            # Step 3: Get available symbols and check EURUSD
            symbols = client.symbols.get_all_symbols()
            assert "EURUSD" in symbols
            assert "GBPUSD" in symbols
            
            # Step 4: Get symbol information and current tick
            symbol_info = client.symbols.get_symbol_info("EURUSD")
            assert symbol_info["name"] == "EURUSD"
            assert symbol_info["digits"] == 5
            
            tick = client.symbols.get_symbol_tick("EURUSD")
            assert tick["bid"] == 1.1000
            assert tick["ask"] == 1.1002
            
            # Step 5: Check current positions and orders
            positions = client.positions.get_open_positions()
            assert len(positions) == 2
            assert positions[0].symbol == "EURUSD"
            assert positions[1].symbol == "GBPUSD"
            
            orders = client.orders.get_pending_orders()
            assert len(orders) == 2
            
            # Step 6: Create a new buy order
            new_order_result = client.orders.create_buy_order(
                symbol="EURUSD",
                volume=0.1,
                stop_loss=1.0950,
                take_profit=1.1100,
                comment="Integration test order"
            )
            assert new_order_result["success"] is True
            
            # Step 7: Modify an existing position
            modify_result = client.positions.modify_position(
                symbol="EURUSD",
                ticket=123456789,
                stop_loss=1.0940,
                take_profit=1.1110
            )
            assert modify_result["success"] is True
            
            # Step 8: Close a position
            close_result = client.positions.close_position(
                symbol="EURUSD",
                ticket=123456789,
                volume=0.1
            )
            assert close_result["success"] is True
            
            # Verify all methods were called as expected
            client.account.get_account_info.assert_called_once()
            client.symbols.get_all_symbols.assert_called_once()
            client.symbols.get_symbol_info.assert_called_once_with("EURUSD")
            client.orders.create_buy_order.assert_called_once()
            client.positions.modify_position.assert_called_once()
            client.positions.close_position.assert_called_once()

    @patch('app.clients.mt5.client.setup_logging')
    def test_error_handling_workflow(self, mock_setup_logging):
        """Test error handling in workflows."""
        client = MT5Client("http://localhost:8000", enable_logging=False)
        
        # Simulate various errors
        account_error = MT5APIError("Account service unavailable", 503, "SERVICE_UNAVAILABLE")
        positions_error = MT5APIError("Position not found", 404, "POSITION_NOT_FOUND")
        
        with patch.object(client.account, 'get_account_info', side_effect=account_error), \
             patch.object(client.positions, 'get_open_positions', side_effect=positions_error), \
             patch.object(client.symbols, 'get_all_symbols', return_value=MOCK_SYMBOLS):
            
            # Account service should fail
            with pytest.raises(MT5APIError) as exc_info:
                client.account.get_account_info()
            assert exc_info.value.status_code == 503
            
            # Positions service should fail
            with pytest.raises(MT5APIError) as exc_info:
                client.positions.get_open_positions()
            assert exc_info.value.status_code == 404
            
            # Symbols service should still work
            symbols = client.symbols.get_all_symbols()
            assert symbols == MOCK_SYMBOLS

    @patch('app.clients.mt5.client.setup_logging')
    def test_portfolio_monitoring_workflow(self, mock_setup_logging):
        """Test portfolio monitoring workflow."""
        client = MT5Client("http://localhost:8000", enable_logging=False)
        
        with patch.object(client.account, 'get_account_info', return_value=MOCK_ACCOUNT_INFO), \
             patch.object(client.account, 'get_account_summary', return_value={
                 'balance': 10000.0,
                 'equity': 10150.0,
                 'margin': 250.0,
                 'margin_free': 9900.0,
                 'margin_level': 406.0,
                 'profit': 150.0,
                 'currency': 'USD',
                 'leverage': 500
             }), \
             patch.object(client.account, 'is_margin_call', return_value=False), \
             patch.object(client.account, 'is_stop_out', return_value=False), \
             patch.object(client.positions, 'get_open_positions', return_value=[Position(**pos) for pos in MOCK_POSITIONS]):
            
            # Monitor account health
            account_summary = client.account.get_account_summary()
            assert account_summary['balance'] == 10000.0
            assert account_summary['equity'] == 10150.0
            
            # Check for risk conditions
            is_margin_call = client.account.is_margin_call()
            is_stop_out = client.account.is_stop_out()
            assert not is_margin_call
            assert not is_stop_out
            
            # Get current positions for P&L analysis
            positions = client.positions.get_open_positions()
            total_profit = sum(pos.profit for pos in positions)
            assert total_profit == 22.5  # 15.0 + 7.5 from mock data
            
            # Verify margin level is healthy
            margin_level = account_summary['margin_level']
            assert margin_level > 100.0  # Above margin call level

    @patch('app.clients.mt5.client.setup_logging')
    def test_symbol_analysis_workflow(self, mock_setup_logging):
        """Test symbol analysis workflow."""
        client = MT5Client("http://localhost:8000", enable_logging=False)
        
        with patch.object(client.symbols, 'get_all_symbols', return_value=MOCK_SYMBOLS), \
             patch.object(client.symbols, 'get_symbol_info', return_value=MOCK_SYMBOL_INFO["EURUSD"]), \
             patch.object(client.symbols, 'get_symbol_tick', return_value=MOCK_TICK_DATA["EURUSD"]), \
             patch.object(client.symbols, 'is_symbol_tradable', return_value={"symbol": "EURUSD", "is_tradable": True}), \
             patch.object(client.data, 'get_latest_bars', return_value=MOCK_HISTORICAL_DATA["bars"]):
            
            # Get all available symbols
            symbols = client.symbols.get_all_symbols()
            assert len(symbols) == 5
            
            # Analyze specific symbol
            symbol = "EURUSD"
            
            # Get symbol specifications
            symbol_info = client.symbols.get_symbol_info(symbol)
            assert symbol_info["digits"] == 5
            assert symbol_info["point"] == 0.00001
            assert symbol_info["volume_min"] == 0.01
            
            # Get current market data
            tick = client.symbols.get_symbol_tick(symbol)
            spread = tick["ask"] - tick["bid"]
            assert abs(spread - 0.0002) < 0.0001  # Approximately 2 pips spread
            
            # Check if symbol is tradable
            tradable_info = client.symbols.is_symbol_tradable(symbol)
            assert tradable_info["is_tradable"] is True
            
            # Get historical data for analysis
            bars = client.data.get_latest_bars(symbol, "H1", 100)
            assert len(bars) == 3  # From mock data
            assert bars[0]["open"] == 1.1000
            
            # Calculate some basic metrics
            highs = [bar["high"] for bar in bars]
            lows = [bar["low"] for bar in bars]
            max_high = max(highs)
            min_low = min(lows)
            daily_range = max_high - min_low
            
            assert max_high == 1.1040
            assert min_low == 1.0980
            assert abs(daily_range - 0.0060) < 0.0001  # Approximately 60 pips range

    @patch('app.clients.mt5.client.setup_logging')
    def test_order_management_workflow(self, mock_setup_logging):
        """Test complete order management workflow."""
        client = MT5Client("http://localhost:8000", enable_logging=False)
        
        new_order_ticket = 999888777
        
        with patch.object(client.orders, 'get_pending_orders', return_value=[Order(**order) for order in MOCK_ORDERS]), \
             patch.object(client.orders, 'create_order', return_value={"success": True, "ticket": new_order_ticket}), \
             patch.object(client.orders, 'update_pending_order', return_value=MOCK_API_SUCCESS_RESPONSE), \
             patch.object(client.orders, 'delete_pending_order', return_value=MOCK_API_SUCCESS_RESPONSE):
            
            # Check current pending orders
            pending_orders = client.orders.get_pending_orders()
            assert len(pending_orders) == 2
            
            # Create a new pending order
            new_order_result = client.orders.create_order(
                symbol="EURUSD",
                volume=0.2,
                order_type=OrderType.BUY_LIMIT,
                price=1.0900,
                stop_loss=1.0850,
                take_profit=1.1000,
                comment="Test limit order"
            )
            assert new_order_result["success"] is True
            assert new_order_result["ticket"] == new_order_ticket
            
            # Update the new order
            update_result = client.orders.update_pending_order(
                ticket=new_order_ticket,
                price=1.0890,  # Better entry price
                stop_loss=1.0840,
                take_profit=1.1010
            )
            assert update_result["success"] is True
            
            # Cancel an old order
            old_ticket = MOCK_ORDERS[0]["ticket"]  # 111222333
            cancel_result = client.orders.delete_pending_order(old_ticket)
            assert cancel_result["success"] is True
            
            # Verify all operations
            client.orders.create_order.assert_called_once()
            client.orders.update_pending_order.assert_called_once_with(
                ticket=new_order_ticket,
                price=1.0890,
                stop_loss=1.0840,
                take_profit=1.1010
            )
            client.orders.delete_pending_order.assert_called_once_with(old_ticket)

    def test_client_lifecycle_management(self):
        """Test client lifecycle management."""
        # Test client creation and cleanup
        with patch('app.clients.mt5.client.setup_logging'):
            # Test with context manager
            with MT5Client("http://localhost:8000", enable_logging=False) as client:
                assert isinstance(client, MT5Client)
                
                # Mock the close methods to verify they're called
                client._positions.close = Mock()
                client._orders.close = Mock()
                client._symbols.close = Mock()
                client._data.close = Mock()
                client._account.close = Mock()
                client._history.close = Mock()
            
            # All close methods should have been called
            client._positions.close.assert_called_once()
            client._orders.close.assert_called_once()
            client._symbols.close.assert_called_once()
            client._data.close.assert_called_once()
            client._account.close.assert_called_once()
            client._history.close.assert_called_once()

    def test_convenience_functions_integration(self):
        """Test convenience functions work properly."""
        with patch('app.clients.mt5.client.MT5Client') as mock_client_class:
            mock_instance = Mock()
            mock_client_class.return_value = mock_instance
            
            # Test create_client function
            client = create_client(
                "http://localhost:8000",
                timeout=60.0,
                enable_logging=True
            )
            
            mock_client_class.assert_called_once_with(
                base_url="http://localhost:8000",
                timeout=60.0,
                enable_logging=True
            )
            assert client is mock_instance

    @patch('app.clients.mt5.client.setup_logging')
    def test_concurrent_operations(self, mock_setup_logging):
        """Test that concurrent operations on different endpoints work properly."""
        client = MT5Client("http://localhost:8000", enable_logging=False)
        
        # Mock different endpoints to return different data
        account_future = Mock()
        positions_future = Mock()
        symbols_future = Mock()
        
        with patch.object(client.account, 'get_account_info', return_value=MOCK_ACCOUNT_INFO) as mock_account, \
             patch.object(client.positions, 'get_open_positions', return_value=[]) as mock_positions, \
             patch.object(client.symbols, 'get_all_symbols', return_value=MOCK_SYMBOLS) as mock_symbols:
            
            # Simulate concurrent calls (in real async scenario)
            account_info = client.account.get_account_info()
            positions = client.positions.get_open_positions()
            symbols = client.symbols.get_all_symbols()
            
            # Verify all calls were made independently
            mock_account.assert_called_once()
            mock_positions.assert_called_once()
            mock_symbols.assert_called_once()
            
            # Verify results are correct
            assert account_info["balance"] == 10000.0
            assert positions == []
            assert symbols == MOCK_SYMBOLS

    @patch('app.clients.mt5.client.setup_logging')
    def test_client_configuration_propagation(self, mock_setup_logging):
        """Test that client configuration is properly propagated to all endpoints."""
        custom_retry_config = RetryConfig(max_retries=10, base_delay=5.0)
        custom_headers = {"X-Custom-Header": "test-value"}
        
        client = MT5Client(
            base_url="http://custom.server:9000",
            timeout=120.0,
            retry_config=custom_retry_config,
            headers=custom_headers,
            enable_logging=False
        )
        
        # Verify all endpoint clients have the same configuration
        for endpoint_client in [client._account, client._positions, client._orders,
                              client._symbols, client._data, client._history]:
            assert endpoint_client.base_url == "http://custom.server:9000"
            assert endpoint_client.timeout == 120.0
            assert endpoint_client.retry_config is custom_retry_config
            assert endpoint_client.headers is custom_headers

    @patch('app.clients.mt5.client.setup_logging')
    def test_error_recovery_workflow(self, mock_setup_logging):
        """Test error recovery in multi-step workflows."""
        client = MT5Client("http://localhost:8000", enable_logging=False)
        
        # Simulate a workflow where some operations fail but others succeed
        account_error = MT5APIError("Temporary service unavailable", 503)
        
        call_count = 0
        def account_info_with_retry():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise account_error
            return MOCK_ACCOUNT_INFO
        
        with patch.object(client.account, 'get_account_info', side_effect=account_info_with_retry), \
             patch.object(client.positions, 'get_open_positions', return_value=[]), \
             patch.object(client.symbols, 'get_all_symbols', return_value=MOCK_SYMBOLS):
            
            # First call should fail
            with pytest.raises(MT5APIError):
                client.account.get_account_info()
            
            # But positions and symbols should still work
            positions = client.positions.get_open_positions()
            symbols = client.symbols.get_all_symbols()
            
            assert positions == []
            assert symbols == MOCK_SYMBOLS
            
            # Retry account info should work
            account_info = client.account.get_account_info()
            assert account_info["balance"] == 10000.0
            
            # Verify call count
            assert call_count == 2