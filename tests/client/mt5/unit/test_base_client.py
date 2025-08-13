"""
Unit tests for BaseClient class.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

import httpx

from app.clients.mt5.base import BaseClient
from app.clients.mt5.utils import RetryConfig
from app.clients.mt5.exceptions import MT5APIError, MT5ValidationError
from app.clients.mt5.models import APIResponse


class TestBaseClient:
    """Test BaseClient class."""

    def test_initialization(self):
        """Test BaseClient initialization."""
        client = BaseClient(
            base_url="http://localhost:8000",
            timeout=30.0,
            retry_config=RetryConfig(max_retries=3),
            headers={"Authorization": "Bearer token"}
        )
        
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30.0
        assert client.retry_config.max_retries == 3
        assert client.headers["Authorization"] == "Bearer token"
        assert client.headers["Content-Type"] == "application/json"
        assert client.headers["Accept"] == "application/json"

    def test_initialization_defaults(self):
        """Test BaseClient initialization with defaults."""
        client = BaseClient("http://localhost:8000")
        
        assert client.base_url == "http://localhost:8000"
        assert client.timeout == 30.0
        assert client.retry_config.max_retries == 3  # default
        assert client.headers["Content-Type"] == "application/json"
        assert client.headers["Accept"] == "application/json"

    def test_base_url_normalization(self):
        """Test base URL normalization (removes trailing slash)."""
        client = BaseClient("http://localhost:8000/")
        assert client.base_url == "http://localhost:8000"
        
        client = BaseClient("http://localhost:8000/api/v1/")
        assert client.base_url == "http://localhost:8000/api/v1"

    def test_sync_client_property(self):
        """Test sync_client property creates httpx.Client."""
        client = BaseClient("http://localhost:8000")
        
        # Initially None
        assert client._sync_client is None
        
        # First access creates client
        sync_client = client.sync_client
        assert isinstance(sync_client, httpx.Client)
        assert client._sync_client is sync_client
        
        # Subsequent access returns same client
        assert client.sync_client is sync_client

    def test_build_url(self):
        """Test URL building."""
        client = BaseClient("http://localhost:8000")
        
        # Basic path
        url = client._build_url("accounts")
        assert url == "http://localhost:8000/accounts"
        
        # Path with leading slash
        url = client._build_url("/accounts")
        assert url == "http://localhost:8000/accounts"
        
        # Complex path
        url = client._build_url("accounts/123/positions")
        assert url == "http://localhost:8000/accounts/123/positions"

    def test_context_manager(self):
        """Test BaseClient as context manager."""
        client = BaseClient("http://localhost:8000")
        
        with client as c:
            assert c is client
            # Access sync client to create it
            _ = c.sync_client
            assert c._sync_client is not None
        
        # Should be closed after context exit
        assert client._sync_client is None

    def test_close_method(self):
        """Test close method."""
        client = BaseClient("http://localhost:8000")
        
        # Create sync client
        _ = client.sync_client
        assert client._sync_client is not None
        
        # Close should clean up
        client.close()
        assert client._sync_client is None

    @patch('httpx.Client')
    def test_handle_response_success(self, mock_client_class):
        """Test successful response handling."""
        client = BaseClient("http://localhost:8000")
        
        # Mock successful response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "data": {"key": "value"},
            "message": "Success"
        }
        
        result = client._handle_response(mock_response)
        assert result == {"key": "value"}

    @patch('httpx.Client')
    def test_handle_response_api_error(self, mock_client_class):
        """Test API error response handling."""
        client = BaseClient("http://localhost:8000")
        
        # Mock error response
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {
            "success": False,
            "data": None,
            "message": "Invalid parameter",
            "error_code": "INVALID_PARAM"
        }
        
        with pytest.raises(MT5APIError) as exc_info:
            client._handle_response(mock_response)
        
        assert exc_info.value.message == "Invalid parameter"
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "INVALID_PARAM"

    @patch('httpx.Client')
    def test_handle_response_json_parse_error(self, mock_client_class):
        """Test response with invalid JSON."""
        client = BaseClient("http://localhost:8000")
        
        # Mock response with invalid JSON
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Invalid JSON")
        mock_response.text = "Invalid JSON response"
        
        with pytest.raises(MT5APIError) as exc_info:
            client._handle_response(mock_response)
        
        assert "Invalid JSON response from server" in exc_info.value.message
        assert exc_info.value.status_code == 200

    @patch('httpx.Client')
    def test_handle_response_non_api_format(self, mock_client_class):
        """Test response that's not in API format."""
        client = BaseClient("http://localhost:8000")
        
        # Mock response with direct data (not API format)
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"direct": "data"}
        
        result = client._handle_response(mock_response)
        assert result == {"direct": "data"}

    @patch('app.clients.mt5.utils.retry_sync')
    @patch('httpx.Client')
    def test_request_sync(self, mock_client_class, mock_retry):
        """Test synchronous request method."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {"result": "ok"}}
        mock_client.request.return_value = mock_response
        
        # Mock retry to just call the function
        mock_retry.side_effect = lambda func, config: func()
        
        client = BaseClient("http://localhost:8000")
        result = client._request_sync("GET", "test", params={"key": "value"})
        
        # Verify request was made correctly
        mock_client.request.assert_called_once_with(
            method="GET",
            url="http://localhost:8000/test",
            params={"key": "value"},
            json=None
        )
        
        # Verify retry was called
        mock_retry.assert_called_once()
        
        # Verify result
        assert result == {"result": "ok"}

    @patch('app.clients.mt5.utils.retry_sync')
    @patch('httpx.Client')
    def test_get_request(self, mock_client_class, mock_retry):
        """Test GET request method."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": ["item1", "item2"]}
        mock_client.request.return_value = mock_response
        
        mock_retry.side_effect = lambda func, config: func()
        
        client = BaseClient("http://localhost:8000")
        result = client.get("items", params={"limit": 10})
        
        # Verify request
        mock_client.request.assert_called_once_with(
            method="GET",
            url="http://localhost:8000/items",
            params={"limit": 10},
            json=None
        )
        
        assert result == ["item1", "item2"]

    @patch('app.clients.mt5.utils.retry_sync')
    @patch('httpx.Client')
    def test_post_request(self, mock_client_class, mock_retry):
        """Test POST request method."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {"id": 123}}
        mock_client.request.return_value = mock_response
        
        mock_retry.side_effect = lambda func, config: func()
        
        client = BaseClient("http://localhost:8000")
        result = client.post("items", json_data={"name": "test"})
        
        # Verify request
        mock_client.request.assert_called_once_with(
            method="POST",
            url="http://localhost:8000/items",
            params=None,
            json={"name": "test"}
        )
        
        assert result == {"id": 123}

    @patch('app.clients.mt5.utils.retry_sync')
    @patch('httpx.Client')
    def test_put_request(self, mock_client_class, mock_retry):
        """Test PUT request method."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {"updated": True}}
        mock_client.request.return_value = mock_response
        
        mock_retry.side_effect = lambda func, config: func()
        
        client = BaseClient("http://localhost:8000")
        result = client.put("items/123", json_data={"name": "updated"})
        
        # Verify request
        mock_client.request.assert_called_once_with(
            method="PUT",
            url="http://localhost:8000/items/123",
            params=None,
            json={"name": "updated"}
        )
        
        assert result == {"updated": True}

    @patch('app.clients.mt5.utils.retry_sync')
    @patch('httpx.Client')
    def test_delete_request(self, mock_client_class, mock_retry):
        """Test DELETE request method."""
        # Setup mocks
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {"deleted": True}}
        mock_client.request.return_value = mock_response
        
        mock_retry.side_effect = lambda func, config: func()
        
        client = BaseClient("http://localhost:8000")
        result = client.delete("items/123")
        
        # Verify request
        mock_client.request.assert_called_once_with(
            method="DELETE",
            url="http://localhost:8000/items/123",
            params=None,
            json=None
        )
        
        assert result == {"deleted": True}

    @patch('app.clients.mt5.utils.retry_sync')
    @patch('httpx.Client')
    def test_request_with_retry_config(self, mock_client_class, mock_retry):
        """Test that retry configuration is passed to retry function."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"success": True, "data": {}}
        mock_client.request.return_value = mock_response
        
        mock_retry.side_effect = lambda func, config: func()
        
        retry_config = RetryConfig(max_retries=5, base_delay=2.0)
        client = BaseClient("http://localhost:8000", retry_config=retry_config)
        
        client.get("test")
        
        # Verify retry was called with our config
        mock_retry.assert_called_once()
        args, kwargs = mock_retry.call_args
        assert args[1] is retry_config  # Second argument should be our retry config