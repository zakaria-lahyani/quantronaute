"""
Unit tests for MT5Client class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

from app.clients.mt5.client import MT5Client, create_client, create_client_with_retry
from app.clients.mt5.utils import RetryConfig
from app.clients.mt5.api.account import AccountClient
from app.clients.mt5.api.positions import PositionsClient
from app.clients.mt5.api.orders import OrdersClient
from app.clients.mt5.api.symbols import SymbolsClient
from app.clients.mt5.api.data import DataClient
from app.clients.mt5.api.history import HistoryClient


class TestMT5Client:
    """Test MT5Client class."""

    @patch('app.clients.mt5.client.setup_logging')
    def test_initialization(self, mock_setup_logging):
        """Test MT5Client initialization."""
        retry_config = RetryConfig(max_retries=5)
        headers = {"Authorization": "Bearer token"}
        
        client = MT5Client(
            base_url="http://localhost:8000",
            timeout=45.0,
            retry_config=retry_config,
            headers=headers,
            enable_logging=True,
            log_level=logging.DEBUG
        )
        
        # Verify base client initialization
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 45.0
        assert client.retry_config is retry_config
        assert client.headers is headers
        
        # Verify logging setup was called
        mock_setup_logging.assert_called_once_with(logging.DEBUG)
        
        # Verify endpoint clients are initialized
        assert isinstance(client._positions, PositionsClient)
        assert isinstance(client._orders, OrdersClient)
        assert isinstance(client._symbols, SymbolsClient)
        assert isinstance(client._data, DataClient)
        assert isinstance(client._account, AccountClient)
        assert isinstance(client._history, HistoryClient)

    @patch('app.clients.mt5.client.setup_logging')
    def test_initialization_with_defaults(self, mock_setup_logging):
        """Test MT5Client initialization with default values."""
        client = MT5Client("http://localhost:8000")
        
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30.0  # default
        assert client.retry_config.max_retries == 3  # default
        mock_setup_logging.assert_called_once_with(logging.INFO)

    @patch('app.clients.mt5.client.setup_logging')
    def test_initialization_logging_disabled(self, mock_setup_logging):
        """Test MT5Client initialization with logging disabled."""
        client = MT5Client("http://localhost:8000", enable_logging=False)
        
        # Logging should not be set up when disabled
        mock_setup_logging.assert_not_called()

    def test_property_access(self):
        """Test accessing endpoint clients via properties."""
        with patch('app.clients.mt5.client.setup_logging'):
            client = MT5Client("http://localhost:8000", enable_logging=False)
            
            # Test all properties return the correct client instances
            assert client.positions is client._positions
            assert client.orders is client._orders
            assert client.symbols is client._symbols
            assert client.data is client._data
            assert client.account is client._account
            assert client.history is client._history

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_health_check(self, mock_get):
        """Test health check method."""
        mock_get.return_value = {"status": "healthy"}
        
        with patch('app.clients.mt5.client.setup_logging'):
            client = MT5Client("http://localhost:8000", enable_logging=False)
            result = client.health_check()
            
            mock_get.assert_called_once_with("health")
            assert result == {"status": "healthy"}

    def test_close_method(self):
        """Test close method calls close on all clients."""
        with patch('app.clients.mt5.client.setup_logging'):
            client = MT5Client("http://localhost:8000", enable_logging=False)
            
            # Mock all client close methods
            client._positions.close = Mock()
            client._orders.close = Mock()
            client._symbols.close = Mock()
            client._data.close = Mock()
            client._account.close = Mock()
            client._history.close = Mock()
            
            # Mock parent close method
            with patch('app.clients.mt5.base.BaseClient.close') as mock_parent_close:
                client.close()
                
                # Verify parent close was called
                mock_parent_close.assert_called_once()
                
                # Verify all endpoint client close methods were called
                client._positions.close.assert_called_once()
                client._orders.close.assert_called_once()
                client._symbols.close.assert_called_once()
                client._data.close.assert_called_once()
                client._account.close.assert_called_once()
                client._history.close.assert_called_once()

    def test_repr_method(self):
        """Test __repr__ method."""
        with patch('app.clients.mt5.client.setup_logging'):
            client = MT5Client("http://localhost:8000", enable_logging=False)
            repr_str = repr(client)
            
            assert "MT5Client" in repr_str
            assert "http://localhost:8000" in repr_str

    def test_get_client_info(self):
        """Test get_client_info method."""
        retry_config = RetryConfig(max_retries=5)
        
        with patch('app.clients.mt5.client.setup_logging'):
            client = MT5Client(
                base_url="http://localhost:8000",
                timeout=45.0,
                retry_config=retry_config,
                enable_logging=False
            )
            
            info = client.get_client_info()
            
            assert info['client_name'] == 'MT5 API Client'
            assert info['version'] == '1.0.0'
            assert info['base_url'] == 'http://localhost:8000'
            assert info['timeout'] == '45.0'
            assert info['retry_max_attempts'] == '5'

    def test_context_manager(self):
        """Test MT5Client as context manager."""
        with patch('app.clients.mt5.client.setup_logging'):
            with MT5Client("http://localhost:8000", enable_logging=False) as client:
                assert isinstance(client, MT5Client)
                
                # Mock close method to verify it's called
                client.close = Mock()
            
            # close should be called when exiting context
            client.close.assert_called_once()

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_endpoint_client_sharing_base_config(self, mock_get):
        """Test that endpoint clients share base configuration."""
        retry_config = RetryConfig(max_retries=7, base_delay=2.0)
        headers = {"Custom-Header": "value"}
        
        with patch('app.clients.mt5.client.setup_logging'):
            client = MT5Client(
                base_url="http://localhost:8000",
                timeout=60.0,
                retry_config=retry_config,
                headers=headers,
                enable_logging=False
            )
            
            # Check that endpoint clients have same configuration
            for endpoint_client in [client._positions, client._orders, client._symbols, 
                                  client._data, client._account, client._history]:
                assert endpoint_client.base_url == "http://localhost:8000"
                assert endpoint_client.timeout == 60.0
                assert endpoint_client.retry_config is retry_config
                assert endpoint_client.headers is headers

    def test_endpoint_clients_independence(self):
        """Test that endpoint client calls are independent."""
        with patch('app.clients.mt5.client.setup_logging'):
            client = MT5Client("http://localhost:8000", enable_logging=False)
            
            # Mock methods on different clients
            client._account.get_account_info = Mock(return_value={"balance": 1000})
            client._positions.get_open_positions = Mock(return_value=[])
            
            # Call methods and verify they're independent
            account_info = client.account.get_account_info()
            positions = client.positions.get_open_positions()
            
            assert account_info == {"balance": 1000}
            assert positions == []
            
            # Verify only the expected methods were called
            client._account.get_account_info.assert_called_once()
            client._positions.get_open_positions.assert_called_once()


class TestConvenienceFunctions:
    """Test convenience functions for client creation."""

    @patch('app.clients.mt5.client.MT5Client')
    def test_create_client(self, mock_client_class):
        """Test create_client convenience function."""
        mock_instance = Mock()
        mock_client_class.return_value = mock_instance
        
        result = create_client(
            base_url="http://localhost:8000",
            timeout=45.0,
            enable_logging=True
        )
        
        # Verify MT5Client was called with correct arguments
        mock_client_class.assert_called_once_with(
            base_url="http://localhost:8000",
            timeout=45.0,
            enable_logging=True
        )
        
        assert result is mock_instance

    @patch('app.clients.mt5.client.MT5Client')
    def test_create_client_with_retry(self, mock_client_class):
        """Test create_client_with_retry convenience function."""
        mock_instance = Mock()
        mock_client_class.return_value = mock_instance
        
        result = create_client_with_retry(
            base_url="http://localhost:8000",
            max_retries=5,
            base_delay=2.0,
            timeout=30.0
        )
        
        # Verify MT5Client was called
        mock_client_class.assert_called_once()
        
        # Verify arguments
        args, kwargs = mock_client_class.call_args
        assert kwargs['base_url'] == "http://localhost:8000"
        assert kwargs['timeout'] == 30.0
        
        # Verify retry config was created correctly
        retry_config = kwargs['retry_config']
        assert isinstance(retry_config, RetryConfig)
        assert retry_config.max_retries == 5
        assert retry_config.base_delay == 2.0
        
        assert result is mock_instance

    @patch('app.clients.mt5.client.MT5Client')
    def test_create_client_with_retry_defaults(self, mock_client_class):
        """Test create_client_with_retry with default values."""
        mock_instance = Mock()
        mock_client_class.return_value = mock_instance
        
        result = create_client_with_retry("http://localhost:8000")
        
        # Verify retry config defaults
        args, kwargs = mock_client_class.call_args
        retry_config = kwargs['retry_config']
        assert retry_config.max_retries == 3  # default
        assert retry_config.base_delay == 1.0  # default


class TestMT5ClientIntegration:
    """Integration-style tests for MT5Client workflow."""

    def test_typical_workflow(self):
        """Test typical client usage workflow."""
        with patch('app.clients.mt5.client.setup_logging'):
            client = MT5Client("http://localhost:8000", enable_logging=False)
            
            # Mock endpoint client methods
            client._account.get_account_info = Mock(return_value={
                "balance": 10000.0, "equity": 10150.0
            })
            client._positions.get_open_positions = Mock(return_value=[
                {"ticket": 123, "symbol": "EURUSD", "profit": 150.0}
            ])
            client._orders.get_pending_orders = Mock(return_value=[])
            client._symbols.get_all_symbols = Mock(return_value=["EURUSD", "GBPUSD"])
            
            # Simulate typical workflow
            account = client.account.get_account_info()
            positions = client.positions.get_open_positions()
            orders = client.orders.get_pending_orders()
            symbols = client.symbols.get_all_symbols()
            
            # Verify results
            assert account["balance"] == 10000.0
            assert len(positions) == 1
            assert positions[0]["symbol"] == "EURUSD"
            assert len(orders) == 0
            assert "EURUSD" in symbols
            assert "GBPUSD" in symbols
            
            # Verify all methods were called
            client._account.get_account_info.assert_called_once()
            client._positions.get_open_positions.assert_called_once()
            client._orders.get_pending_orders.assert_called_once()
            client._symbols.get_all_symbols.assert_called_once()

    def test_error_handling_independence(self):
        """Test that errors in one endpoint don't affect others."""
        with patch('app.clients.mt5.client.setup_logging'):
            client = MT5Client("http://localhost:8000", enable_logging=False)
            
            # Mock one client to raise exception
            client._account.get_account_info = Mock(
                side_effect=Exception("Account service unavailable")
            )
            client._positions.get_open_positions = Mock(return_value=[])
            
            # Should be able to use positions even if account fails
            with pytest.raises(Exception, match="Account service unavailable"):
                client.account.get_account_info()
            
            # Positions should still work
            positions = client.positions.get_open_positions()
            assert positions == []
            
            # Verify both methods were called
            client._account.get_account_info.assert_called_once()
            client._positions.get_open_positions.assert_called_once()

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_health_check_integration(self, mock_get):
        """Test health check in realistic scenario."""
        mock_get.return_value = {
            "status": "healthy",
            "timestamp": "2023-01-01T12:00:00Z",
            "services": {
                "mt5": "connected",
                "database": "connected"
            }
        }
        
        with patch('app.clients.mt5.client.setup_logging'):
            client = MT5Client("http://localhost:8000", enable_logging=False)
            health = client.health_check()
            
            assert health["status"] == "healthy"
            assert "services" in health
            assert health["services"]["mt5"] == "connected"