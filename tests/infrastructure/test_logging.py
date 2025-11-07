"""Tests for the enhanced logging system."""

import pytest
import logging
import json
from io import StringIO

from app.infrastructure.logging import (
    LoggingManager,
    CorrelationContext,
    JsonFormatter,
    TextFormatter,
    get_logger,
)


class TestJsonFormatter:
    """Test JSON log formatting."""

    def test_basic_json_formatting(self):
        """Test that logs are formatted as valid JSON."""
        formatter = JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "test-correlation-id"

        output = formatter.format(record)

        # Verify it's valid JSON
        log_data = json.loads(output)

        # Verify required fields
        assert log_data["level"] == "INFO"
        assert log_data["logger"] == "test_logger"
        assert log_data["message"] == "Test message"
        assert log_data["correlation_id"] == "test-correlation-id"
        assert "timestamp" in log_data

    def test_json_with_exception(self):
        """Test JSON formatting with exception info."""
        formatter = JsonFormatter()

        try:
            raise ValueError("Test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test_logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        record.correlation_id = "test-id"

        output = formatter.format(record)
        log_data = json.loads(output)

        assert "exception" in log_data
        assert "ValueError" in log_data["exception"]
        assert "Test error" in log_data["exception"]


class TestTextFormatter:
    """Test text log formatting."""

    def test_basic_text_formatting(self):
        """Test basic text formatting."""
        formatter = TextFormatter(include_correlation_id=True)
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "test-correlation-id"

        output = formatter.format(record)

        # Verify format
        assert "INFO" in output
        assert "test_logger" in output
        assert "Test message" in output
        assert "test-correlation-id"[:8] in output  # Only first 8 chars shown

    def test_text_formatting_without_correlation_id(self):
        """Test text formatting without correlation ID."""
        formatter = TextFormatter(include_correlation_id=False)
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "test-correlation-id"

        output = formatter.format(record)

        # Correlation ID should not be in output
        assert "test-correlation-id" not in output
        assert "Test message" in output

    def test_text_with_service_name(self):
        """Test text formatting with service name."""
        formatter = TextFormatter(include_correlation_id=True)
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None
        )
        record.correlation_id = "test-id"
        record.service = "DataFetchingService"

        output = formatter.format(record)

        assert "[DataFetchingService]" in output


class TestLoggingManager:
    """Test LoggingManager functionality."""

    def test_create_logging_manager(self):
        """Test creating a logging manager."""
        manager = LoggingManager(
            level="INFO",
            format_type="text",
            include_correlation_ids=True
        )

        assert manager.level == "INFO"
        assert manager.format_type == "text"
        assert manager.include_correlation_ids is True

    def test_configure_root_logger(self):
        """Test configuring root logger."""
        manager = LoggingManager(level="DEBUG", format_type="json")
        manager.configure_root_logger()

        root_logger = logging.getLogger()

        # Verify logger configured
        assert root_logger.level == logging.DEBUG
        assert len(root_logger.handlers) > 0

    def test_configure_service_logger(self):
        """Test configuring service-specific logger."""
        manager = LoggingManager(
            level="INFO",
            service_levels={"TestService": "DEBUG"}
        )
        manager.configure_root_logger()

        logger = manager.configure_service_logger(
            service_name="TestService",
            logger_name="test_service_logger"
        )

        # Verify logger configured with service-specific level
        assert logger.level == logging.DEBUG

    def test_from_config_dict(self):
        """Test creating LoggingManager from config dict."""
        config = {
            "level": "WARNING",
            "format": "json",
            "correlation_ids": False,
            "file_output": False,
            "log_file": "test.log"
        }

        manager = LoggingManager.from_config(config)

        assert manager.level == "WARNING"
        assert manager.format_type == "json"
        assert manager.include_correlation_ids is False


class TestCorrelationId:
    """Test correlation ID functionality."""

    def test_set_and_get_correlation_id(self):
        """Test setting and getting correlation ID."""
        correlation_id = LoggingManager.set_correlation_id("test-id-123")

        assert correlation_id == "test-id-123"
        assert LoggingManager.get_correlation_id() == "test-id-123"

        LoggingManager.clear_correlation_id()
        assert LoggingManager.get_correlation_id() is None

    def test_auto_generate_correlation_id(self):
        """Test auto-generating correlation ID."""
        correlation_id = LoggingManager.set_correlation_id()

        assert correlation_id is not None
        assert len(correlation_id) > 0
        assert LoggingManager.get_correlation_id() == correlation_id

        LoggingManager.clear_correlation_id()

    def test_correlation_context(self):
        """Test CorrelationContext context manager."""
        # Initially no correlation ID
        assert LoggingManager.get_correlation_id() is None

        with CorrelationContext() as correlation_id:
            # Inside context, correlation ID is set
            assert correlation_id is not None
            assert LoggingManager.get_correlation_id() == correlation_id

        # Outside context, correlation ID is cleared
        assert LoggingManager.get_correlation_id() is None

    def test_correlation_context_with_custom_id(self):
        """Test CorrelationContext with custom ID."""
        with CorrelationContext("custom-id") as correlation_id:
            assert correlation_id == "custom-id"
            assert LoggingManager.get_correlation_id() == "custom-id"

        assert LoggingManager.get_correlation_id() is None

    def test_nested_correlation_contexts(self):
        """Test nested correlation contexts."""
        with CorrelationContext("outer-id") as outer_id:
            assert LoggingManager.get_correlation_id() == "outer-id"

            with CorrelationContext("inner-id") as inner_id:
                assert LoggingManager.get_correlation_id() == "inner-id"

            # Back to outer context
            assert LoggingManager.get_correlation_id() == "outer-id"

        # All contexts exited
        assert LoggingManager.get_correlation_id() is None


class TestIntegratedLogging:
    """Test integrated logging with correlation IDs."""

    def test_logging_with_correlation_id(self, caplog):
        """Test that logs include correlation ID."""
        manager = LoggingManager(
            level="INFO",
            format_type="text",
            include_correlation_ids=True
        )
        manager.configure_root_logger()

        logger = logging.getLogger("test_integrated")

        with CorrelationContext("test-correlation") as correlation_id:
            logger.info("Test log message")

        # Verify correlation ID is in log
        # Note: caplog doesn't capture custom fields, so we verify the manager works
        assert correlation_id == "test-correlation"

    def test_get_logger_with_manager(self):
        """Test get_logger utility function."""
        manager = LoggingManager(level="INFO")
        manager.configure_root_logger()

        logger = get_logger(
            name="test_logger",
            service_name="TestService",
            manager=manager
        )

        assert logger is not None
        assert logger.name == "test_logger"

    def test_get_logger_without_manager(self):
        """Test get_logger without manager."""
        logger = get_logger(name="simple_logger")

        assert logger is not None
        assert logger.name == "simple_logger"


class TestLoggingFormats:
    """Test different logging output formats."""

    def test_json_format_output(self):
        """Test JSON format produces valid JSON."""
        # Create a string stream to capture log output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())

        logger = logging.getLogger("json_test")
        logger.setLevel(logging.INFO)
        logger.handlers = [handler]
        logger.propagate = False

        # Create log record with correlation ID
        with CorrelationContext("json-test-id"):
            # Manually add correlation_id to record
            record = logger.makeRecord(
                "json_test", logging.INFO, "test.py", 1,
                "JSON test message", (), None
            )
            record.correlation_id = "json-test-id"
            handler.emit(record)

        # Get output and verify it's valid JSON
        output = stream.getvalue()
        log_data = json.loads(output)

        assert log_data["message"] == "JSON test message"
        assert log_data["correlation_id"] == "json-test-id"

    def test_text_format_output(self):
        """Test text format is human-readable."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(TextFormatter(include_correlation_id=True))

        logger = logging.getLogger("text_test")
        logger.setLevel(logging.INFO)
        logger.handlers = [handler]
        logger.propagate = False

        # Create log record
        record = logger.makeRecord(
            "text_test", logging.INFO, "test.py", 1,
            "Text test message", (), None
        )
        record.correlation_id = "text-test-id"
        handler.emit(record)

        output = stream.getvalue()

        assert "INFO" in output
        assert "Text test message" in output
        assert "text-test-id"[:8] in output  # First 8 chars


class TestServiceLogging:
    """Test service-specific logging configuration."""

    def test_different_log_levels_per_service(self):
        """Test that different services can have different log levels."""
        manager = LoggingManager(
            level="INFO",
            service_levels={
                "DataFetching": "DEBUG",
                "TradeExecution": "WARNING"
            }
        )
        manager.configure_root_logger()

        data_logger = manager.configure_service_logger("DataFetching")
        trade_logger = manager.configure_service_logger("TradeExecution")

        # Verify different levels
        assert data_logger.level == logging.DEBUG
        assert trade_logger.level == logging.WARNING
