"""
Unit tests for MT5 utils module.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import logging
import time

import httpx

from app.clients.mt5.utils import (
    setup_logging, parse_datetime, format_datetime, validate_symbol,
    validate_volume, validate_ticket, RetryConfig, retry_sync,
    build_url, handle_response_errors
)
from app.clients.mt5.exceptions import (
    MT5ConnectionError, MT5TimeoutError, MT5RateLimitError, MT5APIError
)


class TestLogging:
    """Test logging utilities."""

    def test_setup_logging_default(self):
        """Test setup_logging with default parameters."""
        logger = setup_logging()
        
        assert logger.name == 'mt5_client'
        assert logger.level == logging.INFO
        assert len(logger.handlers) > 0

    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom level."""
        logger = setup_logging(logging.DEBUG)
        
        assert logger.level == logging.DEBUG

    def test_setup_logging_no_duplicate_handlers(self):
        """Test that setup_logging doesn't create duplicate handlers."""
        logger1 = setup_logging()
        initial_handler_count = len(logger1.handlers)
        
        logger2 = setup_logging()
        assert len(logger2.handlers) == initial_handler_count
        assert logger1 is logger2  # Should return the same logger instance


class TestDateTimeUtils:
    """Test datetime utilities."""

    def test_parse_datetime_iso_format(self):
        """Test parsing ISO format datetime."""
        dt_str = "2023-01-01T12:00:00"
        result = parse_datetime(dt_str)
        
        assert result == datetime(2023, 1, 1, 12, 0, 0)

    def test_parse_datetime_with_z_suffix(self):
        """Test parsing datetime with Z suffix (UTC)."""
        dt_str = "2023-01-01T12:00:00Z"
        result = parse_datetime(dt_str)
        
        assert result is not None
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 1
        assert result.hour == 12

    def test_parse_datetime_with_timezone(self):
        """Test parsing datetime with timezone offset."""
        dt_str = "2023-01-01T12:00:00+05:00"
        result = parse_datetime(dt_str)
        
        assert result is not None
        assert result.year == 2023
        assert result.hour == 12

    def test_parse_datetime_none(self):
        """Test parsing None datetime."""
        result = parse_datetime(None)
        assert result is None

    def test_parse_datetime_empty_string(self):
        """Test parsing empty string."""
        result = parse_datetime("")
        assert result is None

    def test_parse_datetime_invalid_format(self):
        """Test parsing invalid datetime format."""
        result = parse_datetime("invalid-date-format")
        assert result is None

    def test_format_datetime_from_datetime(self):
        """Test formatting datetime object."""
        dt = datetime(2023, 1, 1, 12, 0, 0)
        result = format_datetime(dt)
        
        assert result == "2023-01-01T12:00:00"

    def test_format_datetime_from_string(self):
        """Test formatting datetime from ISO string."""
        dt_str = "2023-01-01T12:00:00"
        result = format_datetime(dt_str)
        
        assert result == "2023-01-01T12:00:00"

    def test_format_datetime_from_string_with_z(self):
        """Test formatting datetime from string with Z suffix."""
        dt_str = "2023-01-01T12:00:00Z"
        result = format_datetime(dt_str)
        
        assert "2023-01-01T12:00:00" in result

    def test_format_datetime_none(self):
        """Test formatting None datetime."""
        with pytest.raises(ValueError, match="Invalid datetime format"):
            format_datetime(None)

    def test_format_datetime_invalid_type(self):
        """Test formatting invalid datetime type."""
        with pytest.raises(ValueError, match="Invalid datetime format"):
            format_datetime(12345)

    def test_format_datetime_invalid_string(self):
        """Test formatting invalid datetime string."""
        with pytest.raises(ValueError, match="Invalid datetime format"):
            format_datetime("not-a-date")


class TestValidationUtils:
    """Test validation utilities."""

    def test_validate_symbol_valid(self):
        """Test validating valid symbol."""
        result = validate_symbol("eurusd")
        assert result == "EURUSD"
        
        result = validate_symbol("GBPUSD")
        assert result == "GBPUSD"
        
        result = validate_symbol("  usdjpy  ")
        assert result == "USDJPY"

    def test_validate_symbol_invalid(self):
        """Test validating invalid symbol."""
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            validate_symbol("")
        
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            validate_symbol(None)
        
        with pytest.raises(ValueError, match="Symbol must be a non-empty string"):
            validate_symbol(123)

    def test_validate_volume_valid(self):
        """Test validating valid volume."""
        assert validate_volume(0.1) == 0.1
        assert validate_volume(1.0) == 1.0
        assert validate_volume(100) == 100.0
        assert validate_volume(0.01) == 0.01

    def test_validate_volume_invalid(self):
        """Test validating invalid volume."""
        with pytest.raises(ValueError, match="Volume must be a positive number"):
            validate_volume(0)
        
        with pytest.raises(ValueError, match="Volume must be a positive number"):
            validate_volume(-0.1)
        
        with pytest.raises(ValueError, match="Volume must be a positive number"):
            validate_volume("invalid")

    def test_validate_ticket_valid(self):
        """Test validating valid ticket."""
        assert validate_ticket(123456789) == 123456789
        assert validate_ticket(1) == 1

    def test_validate_ticket_invalid(self):
        """Test validating invalid ticket."""
        with pytest.raises(ValueError, match="Ticket must be a positive integer"):
            validate_ticket(0)
        
        with pytest.raises(ValueError, match="Ticket must be a positive integer"):
            validate_ticket(-123)
        
        with pytest.raises(ValueError, match="Ticket must be a positive integer"):
            validate_ticket(123.45)
        
        with pytest.raises(ValueError, match="Ticket must be a positive integer"):
            validate_ticket("123")


class TestRetryConfig:
    """Test RetryConfig class."""

    def test_retry_config_defaults(self):
        """Test RetryConfig with default values."""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True

    def test_retry_config_custom_values(self):
        """Test RetryConfig with custom values."""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=3.0,
            jitter=False
        )
        
        assert config.max_retries == 5
        assert config.base_delay == 2.0
        assert config.max_delay == 120.0
        assert config.exponential_base == 3.0
        assert config.jitter is False


class TestRetrySyncFunction:
    """Test retry_sync function."""

    def test_retry_sync_success_first_attempt(self):
        """Test retry_sync with successful first attempt."""
        config = RetryConfig(max_retries=3)
        
        def successful_func():
            return "success"
        
        result = retry_sync(successful_func, config)
        assert result == "success"

    def test_retry_sync_success_after_retry(self):
        """Test retry_sync with success after retry."""
        config = RetryConfig(max_retries=3, base_delay=0.01)  # Fast for testing
        
        call_count = 0
        def failing_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.ConnectError("Connection failed")
            return "success"
        
        with patch('time.sleep'):  # Don't actually sleep in tests
            result = retry_sync(failing_then_success, config)
        
        assert result == "success"
        assert call_count == 3

    def test_retry_sync_max_retries_exceeded_connect_error(self):
        """Test retry_sync when max retries exceeded with connect error."""
        config = RetryConfig(max_retries=2, base_delay=0.01)
        
        def always_fails():
            raise httpx.ConnectError("Connection failed")
        
        with patch('time.sleep'):
            with pytest.raises(MT5ConnectionError, match="Failed to connect to MT5 API"):
                retry_sync(always_fails, config)

    def test_retry_sync_max_retries_exceeded_timeout_error(self):
        """Test retry_sync when max retries exceeded with timeout error."""
        config = RetryConfig(max_retries=2, base_delay=0.01)
        
        def always_times_out():
            raise httpx.TimeoutException("Request timed out")
        
        with patch('time.sleep'):
            with pytest.raises(MT5TimeoutError, match="Request to MT5 API timed out"):
                retry_sync(always_times_out, config)

    def test_retry_sync_http_status_error_no_retry(self):
        """Test retry_sync doesn't retry HTTP status errors (except 429)."""
        config = RetryConfig(max_retries=3)
        
        def http_error():
            response = Mock()
            response.status_code = 400
            raise httpx.HTTPStatusError("Bad Request", request=Mock(), response=response)
        
        with pytest.raises(httpx.HTTPStatusError):
            retry_sync(http_error, config)

    def test_retry_sync_rate_limit_with_retry_after(self):
        """Test retry_sync handles 429 rate limit with Retry-After header."""
        config = RetryConfig(max_retries=3, base_delay=0.01)
        
        call_count = 0
        def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                response = Mock()
                response.status_code = 429
                response.headers = {'Retry-After': '1'}
                raise httpx.HTTPStatusError("Rate Limited", request=Mock(), response=response)
            return "success"
        
        with patch('time.sleep') as mock_sleep:
            result = retry_sync(rate_limited, config)
        
        assert result == "success"
        mock_sleep.assert_called_once_with(1)  # Should sleep for Retry-After time

    def test_retry_sync_rate_limit_max_retries_exceeded(self):
        """Test retry_sync raises MT5RateLimitError when rate limit exceeded."""
        config = RetryConfig(max_retries=1, base_delay=0.01)
        
        def always_rate_limited():
            response = Mock()
            response.status_code = 429
            response.headers = {'Retry-After': '60'}
            raise httpx.HTTPStatusError("Rate Limited", request=Mock(), response=response)
        
        with patch('time.sleep'):
            with pytest.raises(MT5RateLimitError, match="Rate limit exceeded"):
                retry_sync(always_rate_limited, config)

    def test_retry_sync_exponential_backoff(self):
        """Test retry_sync uses exponential backoff."""
        config = RetryConfig(max_retries=3, base_delay=1.0, exponential_base=2.0, jitter=False)
        
        call_count = 0
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection failed")
        
        with patch('time.sleep') as mock_sleep:
            with pytest.raises(MT5ConnectionError):
                retry_sync(always_fails, config)
        
        # Should have called sleep with exponentially increasing delays
        expected_delays = [1.0, 2.0, 4.0]  # base_delay * (exponential_base ** attempt)
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays

    def test_retry_sync_with_jitter(self):
        """Test retry_sync applies jitter to delays."""
        config = RetryConfig(max_retries=2, base_delay=1.0, jitter=True)
        
        call_count = 0
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection failed")
        
        with patch('time.sleep') as mock_sleep, patch('random.random', return_value=0.5):
            with pytest.raises(MT5ConnectionError):
                retry_sync(always_fails, config)
        
        # With jitter and random=0.5, delays should be multiplied by 0.75 (0.5 + 0.5 * 0.5)
        expected_delays = [0.75, 1.5]  # [1.0 * 0.75, 2.0 * 0.75]
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert actual_delays == expected_delays

    def test_retry_sync_max_delay_limit(self):
        """Test retry_sync respects max_delay limit."""
        config = RetryConfig(max_retries=3, base_delay=10.0, max_delay=5.0, jitter=False)
        
        call_count = 0
        def always_fails():
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("Connection failed")
        
        with patch('time.sleep') as mock_sleep:
            with pytest.raises(MT5ConnectionError):
                retry_sync(always_fails, config)
        
        # All delays should be capped at max_delay (5.0)
        actual_delays = [call.args[0] for call in mock_sleep.call_args_list]
        assert all(delay <= 5.0 for delay in actual_delays)


class TestBuildUrl:
    """Test build_url utility."""

    def test_build_url_basic(self):
        """Test basic URL building."""
        url = build_url("http://localhost:8000", "accounts")
        assert url == "http://localhost:8000/accounts"

    def test_build_url_with_trailing_slash(self):
        """Test URL building with trailing slash in base URL."""
        url = build_url("http://localhost:8000/", "accounts")
        assert url == "http://localhost:8000/accounts"

    def test_build_url_with_leading_slash_in_path(self):
        """Test URL building with leading slash in path."""
        url = build_url("http://localhost:8000", "/accounts")
        assert url == "http://localhost:8000/accounts"

    def test_build_url_with_params(self):
        """Test URL building with parameters."""
        url = build_url("http://localhost:8000", "accounts", limit=10, offset=20)
        
        # URL should contain both parameters (order might vary)
        assert "http://localhost:8000/accounts?" in url
        assert "limit=10" in url
        assert "offset=20" in url

    def test_build_url_with_none_params(self):
        """Test URL building with None parameters (should be filtered out)."""
        url = build_url("http://localhost:8000", "accounts", limit=10, offset=None, page=None)
        
        assert url == "http://localhost:8000/accounts?limit=10"

    def test_build_url_no_params(self):
        """Test URL building with no parameters."""
        url = build_url("http://localhost:8000", "accounts", **{})
        assert url == "http://localhost:8000/accounts"


class TestHandleResponseErrors:
    """Test handle_response_errors utility."""

    def test_handle_response_errors_success(self):
        """Test handle_response_errors with successful response."""
        response = Mock()
        response.status_code = 200
        
        # Should not raise any exception
        handle_response_errors(response)

    def test_handle_response_errors_client_error(self):
        """Test handle_response_errors with client error."""
        response = Mock()
        response.status_code = 400
        response.json.return_value = {
            "message": "Bad Request",
            "error_code": "INVALID_PARAM"
        }
        response.text = "Bad Request"
        
        with pytest.raises(MT5APIError) as exc_info:
            handle_response_errors(response)
        
        assert exc_info.value.message == "Bad Request"
        assert exc_info.value.status_code == 400
        assert exc_info.value.error_code == "INVALID_PARAM"

    def test_handle_response_errors_server_error(self):
        """Test handle_response_errors with server error."""
        response = Mock()
        response.status_code = 500
        response.json.return_value = {"message": "Internal Server Error"}
        response.text = "Internal Server Error"
        
        with pytest.raises(MT5APIError) as exc_info:
            handle_response_errors(response)
        
        assert exc_info.value.message == "Internal Server Error"
        assert exc_info.value.status_code == 500

    def test_handle_response_errors_json_parse_failure(self):
        """Test handle_response_errors when JSON parsing fails."""
        response = Mock()
        response.status_code = 404
        response.json.side_effect = Exception("Invalid JSON")
        response.text = "Not Found"
        
        with pytest.raises(MT5APIError) as exc_info:
            handle_response_errors(response)
        
        assert exc_info.value.message == "HTTP 404 error"
        assert exc_info.value.status_code == 404
        assert exc_info.value.error_code is None

    def test_handle_response_errors_no_message_in_response(self):
        """Test handle_response_errors when response has no message."""
        response = Mock()
        response.status_code = 403
        response.json.return_value = {"error_code": "FORBIDDEN"}
        response.text = "Forbidden"
        
        with pytest.raises(MT5APIError) as exc_info:
            handle_response_errors(response)
        
        assert exc_info.value.message == "HTTP 403 error"
        assert exc_info.value.status_code == 403
        assert exc_info.value.error_code == "FORBIDDEN"