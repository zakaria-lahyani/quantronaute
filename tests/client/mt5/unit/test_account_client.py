"""
Unit tests for AccountClient class.
"""

import pytest
from unittest.mock import Mock, patch

from app.clients.mt5.api.account import AccountClient
from app.clients.mt5.exceptions import MT5APIError


class TestAccountClient:
    """Test AccountClient class."""

    def test_initialization(self):
        """Test AccountClient initialization."""
        client = AccountClient("http://localhost:8000")
        
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30.0

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_account_info(self, mock_get):
        """Test get_account_info method."""
        mock_account_data = {
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
            "profit": 150.0,
            "company": "MetaQuotes Ltd"
        }
        mock_get.return_value = mock_account_data
        
        client = AccountClient("http://localhost:8000")
        result = client.get_account_info()
        
        mock_get.assert_called_once_with("account")
        assert result == mock_account_data
        assert result["balance"] == 10000.0
        assert result["equity"] == 10150.0
        assert result["leverage"] == 500

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_balance(self, mock_get):
        """Test get_balance method."""
        mock_balance_data = {"balance": 10000.0}
        mock_get.return_value = mock_balance_data
        
        client = AccountClient("http://localhost:8000")
        result = client.get_balance()
        
        mock_get.assert_called_once_with("account/balance")
        assert result == mock_balance_data
        assert result["balance"] == 10000.0

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_equity(self, mock_get):
        """Test get_equity method."""
        mock_equity_data = {"equity": 10150.0}
        mock_get.return_value = mock_equity_data
        
        client = AccountClient("http://localhost:8000")
        result = client.get_equity()
        
        mock_get.assert_called_once_with("account/equity")
        assert result == mock_equity_data
        assert result["equity"] == 10150.0

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_margin_info(self, mock_get):
        """Test get_margin_info method."""
        mock_margin_data = {
            "margin": 250.0,
            "margin_free": 9900.0,
            "margin_level": 406.0
        }
        mock_get.return_value = mock_margin_data
        
        client = AccountClient("http://localhost:8000")
        result = client.get_margin_info()
        
        mock_get.assert_called_once_with("account/margin")
        assert result == mock_margin_data
        assert result["margin"] == 250.0
        assert result["margin_free"] == 9900.0
        assert result["margin_level"] == 406.0

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_leverage(self, mock_get):
        """Test get_leverage method."""
        mock_leverage_data = {"leverage": 500}
        mock_get.return_value = mock_leverage_data
        
        client = AccountClient("http://localhost:8000")
        result = client.get_leverage()
        
        mock_get.assert_called_once_with("account/leverage")
        assert result == mock_leverage_data
        assert result["leverage"] == 500

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_account_summary(self, mock_get):
        """Test get_account_summary method."""
        mock_account_data = {
            "login": 12345678,
            "balance": 10000.0,
            "equity": 10150.0,
            "margin": 250.0,
            "margin_free": 9900.0,
            "margin_level": 406.0,
            "profit": 150.0,
            "currency": "USD",
            "leverage": 500
        }
        mock_get.return_value = mock_account_data
        
        client = AccountClient("http://localhost:8000")
        result = client.get_account_summary()
        
        mock_get.assert_called_once_with("account")
        
        expected_summary = {
            'balance': 10000.0,
            'equity': 10150.0,
            'margin': 250.0,
            'margin_free': 9900.0,
            'margin_level': 406.0,
            'profit': 150.0,
            'currency': 'USD',
            'leverage': 500,
        }
        
        assert result == expected_summary

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_get_account_summary_missing_fields(self, mock_get):
        """Test get_account_summary with missing optional fields."""
        mock_account_data = {
            "login": 12345678,
            "balance": 10000.0,
            "equity": 10150.0
            # Missing other fields
        }
        mock_get.return_value = mock_account_data
        
        client = AccountClient("http://localhost:8000")
        result = client.get_account_summary()
        
        # Should use defaults for missing fields
        assert result['balance'] == 10000.0
        assert result['equity'] == 10150.0
        assert result['margin'] == 0.0  # default
        assert result['margin_free'] == 0.0  # default
        assert result['margin_level'] == 0.0  # default
        assert result['profit'] == 0.0  # default
        assert result['currency'] == ''  # default
        assert result['leverage'] == 1  # default

    @patch.object(AccountClient, 'get_margin_info')
    def test_get_free_margin(self, mock_get_margin_info):
        """Test get_free_margin method."""
        mock_margin_data = {
            "margin": 250.0,
            "margin_free": 9900.0,
            "margin_level": 406.0
        }
        mock_get_margin_info.return_value = mock_margin_data
        
        client = AccountClient("http://localhost:8000")
        result = client.get_free_margin()
        
        mock_get_margin_info.assert_called_once()
        assert result == 9900.0

    @patch.object(AccountClient, 'get_margin_info')
    def test_get_free_margin_missing(self, mock_get_margin_info):
        """Test get_free_margin when margin_free is missing."""
        mock_get_margin_info.return_value = {}
        
        client = AccountClient("http://localhost:8000")
        result = client.get_free_margin()
        
        assert result == 0.0  # default

    @patch.object(AccountClient, 'get_margin_info')
    def test_get_margin_level(self, mock_get_margin_info):
        """Test get_margin_level method."""
        mock_margin_data = {"margin_level": 406.0}
        mock_get_margin_info.return_value = mock_margin_data
        
        client = AccountClient("http://localhost:8000")
        result = client.get_margin_level()
        
        mock_get_margin_info.assert_called_once()
        assert result == 406.0

    @patch.object(AccountClient, 'get_account_info')
    def test_get_profit(self, mock_get_account_info):
        """Test get_profit method."""
        mock_account_data = {"profit": 150.0}
        mock_get_account_info.return_value = mock_account_data
        
        client = AccountClient("http://localhost:8000")
        result = client.get_profit()
        
        mock_get_account_info.assert_called_once()
        assert result == 150.0

    @patch.object(AccountClient, 'get_margin_level')
    def test_is_margin_call_true(self, mock_get_margin_level):
        """Test is_margin_call method returns True when below threshold."""
        mock_get_margin_level.return_value = 50.0  # Below default 100%
        
        client = AccountClient("http://localhost:8000")
        result = client.is_margin_call()
        
        mock_get_margin_level.assert_called_once()
        assert result is True

    @patch.object(AccountClient, 'get_margin_level')
    def test_is_margin_call_false(self, mock_get_margin_level):
        """Test is_margin_call method returns False when above threshold."""
        mock_get_margin_level.return_value = 200.0  # Above default 100%
        
        client = AccountClient("http://localhost:8000")
        result = client.is_margin_call()
        
        mock_get_margin_level.assert_called_once()
        assert result is False

    @patch.object(AccountClient, 'get_margin_level')
    def test_is_margin_call_custom_level(self, mock_get_margin_level):
        """Test is_margin_call method with custom margin call level."""
        mock_get_margin_level.return_value = 80.0
        
        client = AccountClient("http://localhost:8000")
        result = client.is_margin_call(margin_call_level=90.0)
        
        mock_get_margin_level.assert_called_once()
        assert result is True  # 80% < 90%

    @patch.object(AccountClient, 'get_margin_level')
    def test_is_margin_call_zero_margin_level(self, mock_get_margin_level):
        """Test is_margin_call when margin level is zero."""
        mock_get_margin_level.return_value = 0.0
        
        client = AccountClient("http://localhost:8000")
        result = client.is_margin_call()
        
        mock_get_margin_level.assert_called_once()
        assert result is False  # Should return False for zero margin level

    @patch.object(AccountClient, 'get_margin_level')
    def test_is_stop_out_true(self, mock_get_margin_level):
        """Test is_stop_out method returns True when below threshold."""
        mock_get_margin_level.return_value = 30.0  # Below default 50%
        
        client = AccountClient("http://localhost:8000")
        result = client.is_stop_out()
        
        mock_get_margin_level.assert_called_once()
        assert result is True

    @patch.object(AccountClient, 'get_margin_level')
    def test_is_stop_out_false(self, mock_get_margin_level):
        """Test is_stop_out method returns False when above threshold."""
        mock_get_margin_level.return_value = 100.0  # Above default 50%
        
        client = AccountClient("http://localhost:8000")
        result = client.is_stop_out()
        
        mock_get_margin_level.assert_called_once()
        assert result is False

    @patch.object(AccountClient, 'get_margin_level')
    def test_is_stop_out_custom_level(self, mock_get_margin_level):
        """Test is_stop_out method with custom stop out level."""
        mock_get_margin_level.return_value = 40.0
        
        client = AccountClient("http://localhost:8000")
        result = client.is_stop_out(stop_out_level=45.0)
        
        mock_get_margin_level.assert_called_once()
        assert result is True  # 40% < 45%

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_api_error_handling(self, mock_get):
        """Test API error handling."""
        mock_get.side_effect = MT5APIError(
            message="Account not found",
            status_code=404,
            error_code="ACCOUNT_NOT_FOUND"
        )
        
        client = AccountClient("http://localhost:8000")
        
        with pytest.raises(MT5APIError) as exc_info:
            client.get_account_info()
        
        assert exc_info.value.message == "Account not found"
        assert exc_info.value.status_code == 404
        assert exc_info.value.error_code == "ACCOUNT_NOT_FOUND"

    def test_inheritance(self):
        """Test that AccountClient properly inherits from BaseClient."""
        client = AccountClient("http://localhost:8000")
        
        # Should have BaseClient attributes
        assert hasattr(client, 'base_url')
        assert hasattr(client, 'timeout')
        assert hasattr(client, 'retry_config')
        assert hasattr(client, 'headers')
        
        # Should have BaseClient methods
        assert hasattr(client, 'get')
        assert hasattr(client, 'post')
        assert hasattr(client, 'put')
        assert hasattr(client, 'delete')
        assert hasattr(client, 'close')

    @patch('app.clients.mt5.base.BaseClient.get')
    def test_multiple_calls_independence(self, mock_get):
        """Test that multiple method calls are independent."""
        mock_get.side_effect = [
            {"balance": 10000.0},  # First call
            {"equity": 10150.0},   # Second call
            {"margin": 250.0}      # Third call
        ]
        
        client = AccountClient("http://localhost:8000")
        
        balance = client.get_balance()
        equity = client.get_equity()
        margin = client.get_margin_info()
        
        # Verify all calls were made with correct paths
        expected_calls = [
            ('account/balance',),
            ('account/equity',),
            ('account/margin',)
        ]
        
        actual_calls = [call.args for call in mock_get.call_args_list]
        assert actual_calls == expected_calls
        
        # Verify return values
        assert balance == {"balance": 10000.0}
        assert equity == {"equity": 10150.0}
        assert margin == {"margin": 250.0}