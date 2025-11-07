"""
Tests for DataFetchingService.

These tests verify that DataFetchingService correctly:
- Initializes with proper configuration
- Fetches streaming data from DataSourceManager
- Detects new candles
- Publishes DataFetchedEvent and NewCandleEvent
- Handles errors gracefully
- Tracks metrics correctly
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
from datetime import datetime, timedelta

from app.services.data_fetching import DataFetchingService
from app.services.base import ServiceStatus
from app.infrastructure.event_bus import EventBus
from app.events.data_events import DataFetchedEvent, NewCandleEvent, DataFetchErrorEvent
from app.data.data_manger import DataSourceManager
from tests.fixtures.market_data import create_mock_bars, create_mock_bar
from tests.mocks.mock_event_bus import MockEventBus


class TestDataFetchingServiceInitialization:
    """Test DataFetchingService initialization."""

    def test_initialization_with_valid_config(self):
        """Test service initializes correctly with valid config."""
        event_bus = EventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5", "15"],
            "candle_index": 1,
            "nbr_bars": 3,
        }

        service = DataFetchingService(
            event_bus=event_bus,
            data_source=data_source,
            config=config,
        )

        assert service.service_name == "DataFetchingService"
        assert service.symbol == "EURUSD"
        assert service.timeframes == ["1", "5", "15"]
        assert service.candle_index == 1
        assert service.nbr_bars == 3
        assert service._status == ServiceStatus.INITIALIZING

    def test_initialization_with_default_values(self):
        """Test service uses default values for optional config."""
        event_bus = EventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "GBPUSD",
            "timeframes": ["5"],
        }

        service = DataFetchingService(
            event_bus=event_bus,
            data_source=data_source,
            config=config,
        )

        # Should use defaults
        assert service.candle_index == 1
        assert service.nbr_bars == 3

    def test_initialization_without_config_raises_error(self):
        """Test that missing config raises ValueError."""
        event_bus = EventBus()
        data_source = Mock(spec=DataSourceManager)

        with pytest.raises(ValueError, match="requires configuration"):
            DataFetchingService(
                event_bus=event_bus,
                data_source=data_source,
                config=None,
            )

    def test_initialization_without_symbol_raises_error(self):
        """Test that missing symbol raises ValueError."""
        event_bus = EventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {"timeframes": ["1", "5"]}

        with pytest.raises(ValueError, match="must include 'symbol'"):
            DataFetchingService(
                event_bus=event_bus,
                data_source=data_source,
                config=config,
            )

    def test_initialization_without_timeframes_raises_error(self):
        """Test that missing timeframes raises ValueError."""
        event_bus = EventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {"symbol": "EURUSD"}

        with pytest.raises(ValueError, match="must include non-empty 'timeframes'"):
            DataFetchingService(
                event_bus=event_bus,
                data_source=data_source,
                config=config,
            )

    def test_initialization_with_empty_timeframes_raises_error(self):
        """Test that empty timeframes list raises ValueError."""
        event_bus = EventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": [],
        }

        with pytest.raises(ValueError, match="must include non-empty 'timeframes'"):
            DataFetchingService(
                event_bus=event_bus,
                data_source=data_source,
                config=config,
            )

    def test_last_known_bars_initialized_correctly(self):
        """Test that last_known_bars dict is initialized for all timeframes."""
        event_bus = EventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5", "15"],
        }

        service = DataFetchingService(
            event_bus=event_bus,
            data_source=data_source,
            config=config,
        )

        assert len(service.last_known_bars) == 3
        assert "1" in service.last_known_bars
        assert "5" in service.last_known_bars
        assert "15" in service.last_known_bars
        assert service.last_known_bars["1"] is None
        assert service.last_known_bars["5"] is None
        assert service.last_known_bars["15"] is None


class TestDataFetchingServiceLifecycle:
    """Test service lifecycle (start/stop)."""

    def test_start_changes_status_to_running(self):
        """Test that start() sets status to RUNNING."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        assert service._status == ServiceStatus.INITIALIZING

        service.start()

        assert service._status == ServiceStatus.RUNNING

    def test_stop_changes_status_to_stopped(self):
        """Test that stop() sets status to STOPPED."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()
        assert service._status == ServiceStatus.RUNNING

        service.stop()

        assert service._status == ServiceStatus.STOPPED

    def test_stop_clears_last_known_bars(self):
        """Test that stop() clears last_known_bars."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        # Set some bars
        service.last_known_bars["1"] = create_mock_bar()
        service.last_known_bars["5"] = create_mock_bar()

        service.start()
        service.stop()

        # Should be cleared
        assert len(service.last_known_bars) == 0


class TestDataFetchingServiceHealthCheck:
    """Test health check functionality."""

    def test_health_check_healthy_when_running(self):
        """Test health check returns healthy when running."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        health = service.health_check()

        assert health.is_healthy is True
        assert health.status == ServiceStatus.RUNNING

    def test_health_check_unhealthy_when_stopped(self):
        """Test health check returns unhealthy when stopped."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()
        service.stop()

        health = service.health_check()

        assert health.is_healthy is False
        assert health.status == ServiceStatus.STOPPED

    def test_health_check_unhealthy_with_many_errors(self):
        """Test health check returns unhealthy with many errors."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        # Simulate many errors
        service._metrics["fetch_errors"] = 15

        health = service.health_check()

        assert health.is_healthy is False


class TestDataFetchingStreamingData:
    """Test fetching streaming data."""

    def test_fetch_streaming_data_success(self):
        """Test successful data fetch publishes DataFetchedEvent."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        # Mock data source to return bars
        mock_bars = create_mock_bars(num_bars=3)
        data_source.get_stream_data.return_value = mock_bars

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
            "nbr_bars": 3,
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        success_count = service.fetch_streaming_data()

        # Should succeed
        assert success_count == 1

        # Should call data source
        data_source.get_stream_data.assert_called_once_with(
            symbol="EURUSD",
            timeframe="1",
            nbr_bars=3,
        )

        # Should publish DataFetchedEvent
        events = mock_bus.get_published_events(DataFetchedEvent)
        assert len(events) == 1
        assert events[0].symbol == "EURUSD"
        assert events[0].timeframe == "1"
        assert events[0].num_bars == 3

    def test_fetch_streaming_data_multiple_timeframes(self):
        """Test fetching data for multiple timeframes."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        # Mock data source to return bars
        mock_bars = create_mock_bars(num_bars=3)
        data_source.get_stream_data.return_value = mock_bars

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5", "15"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        success_count = service.fetch_streaming_data()

        # Should succeed for all 3 timeframes
        assert success_count == 3

        # Should call data source 3 times
        assert data_source.get_stream_data.call_count == 3

        # Should publish 3 DataFetchedEvents
        events = mock_bus.get_published_events(DataFetchedEvent)
        assert len(events) == 3

    def test_fetch_streaming_data_when_not_running(self):
        """Test fetch returns 0 when service not running."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        # Don't start the service
        success_count = service.fetch_streaming_data()

        assert success_count == 0
        data_source.get_stream_data.assert_not_called()

    def test_fetch_streaming_data_with_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        # Return empty DataFrame
        data_source.get_stream_data.return_value = pd.DataFrame()

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        success_count = service.fetch_streaming_data()

        # Should fail (0 successes)
        assert success_count == 0

        # Should publish DataFetchErrorEvent
        error_events = mock_bus.get_published_events(DataFetchErrorEvent)
        assert len(error_events) == 1
        assert "Empty DataFrame" in error_events[0].error

    def test_fetch_streaming_data_with_exception(self):
        """Test handling of data source exception."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        # Raise exception
        data_source.get_stream_data.side_effect = Exception("Connection error")

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        success_count = service.fetch_streaming_data()

        # Should fail
        assert success_count == 0

        # Should publish DataFetchErrorEvent
        error_events = mock_bus.get_published_events(DataFetchErrorEvent)
        assert len(error_events) == 1
        assert error_events[0].symbol == "EURUSD"
        assert error_events[0].timeframe == "1"
        assert "Connection error" in error_events[0].error


class TestNewCandleDetection:
    """Test new candle detection logic."""

    def test_new_candle_detected_on_first_fetch(self):
        """Test that first fetch always detects new candle."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        # Mock bars
        mock_bars = create_mock_bars(num_bars=3)
        data_source.get_stream_data.return_value = mock_bars

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
            "candle_index": 1,
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        # First fetch - should detect new candle
        service.fetch_streaming_data()

        # Should publish NewCandleEvent
        candle_events = mock_bus.get_published_events(NewCandleEvent)
        assert len(candle_events) == 1
        assert candle_events[0].symbol == "EURUSD"
        assert candle_events[0].timeframe == "1"

    def test_new_candle_detected_when_time_changes(self):
        """Test new candle detected when bar time changes."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
            "candle_index": 1,
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        # First fetch
        bars1 = create_mock_bars(num_bars=3, start_time=datetime.now() - timedelta(minutes=10))
        data_source.get_stream_data.return_value = bars1
        service.fetch_streaming_data()

        # Should have 1 new candle event
        assert len(mock_bus.get_published_events(NewCandleEvent)) == 1

        # Second fetch with newer time
        bars2 = create_mock_bars(num_bars=3, start_time=datetime.now() - timedelta(minutes=5))
        data_source.get_stream_data.return_value = bars2
        service.fetch_streaming_data()

        # Should have 2 new candle events
        assert len(mock_bus.get_published_events(NewCandleEvent)) == 2

    def test_no_new_candle_when_time_unchanged(self):
        """Test no new candle when bar time hasn't changed."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
            "candle_index": 1,
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        # First fetch
        bars = create_mock_bars(num_bars=3, start_time=datetime.now() - timedelta(minutes=10))
        data_source.get_stream_data.return_value = bars
        service.fetch_streaming_data()

        # Should have 1 new candle event
        assert len(mock_bus.get_published_events(NewCandleEvent)) == 1

        # Second fetch with same bars
        data_source.get_stream_data.return_value = bars
        service.fetch_streaming_data()

        # Should still have only 1 new candle event (no new one)
        assert len(mock_bus.get_published_events(NewCandleEvent)) == 1

    def test_last_known_bar_updated_on_new_candle(self):
        """Test that last_known_bar is updated when new candle detected."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
            "candle_index": 1,
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        # First fetch
        bars = create_mock_bars(num_bars=3)
        data_source.get_stream_data.return_value = bars
        service.fetch_streaming_data()

        # Should have updated last_known_bar
        assert service.last_known_bars["1"] is not None
        expected_bar = bars.iloc[-1]
        actual_bar = service.last_known_bars["1"]

        # Compare timestamps
        assert pd.to_datetime(actual_bar["time"]) == pd.to_datetime(expected_bar["time"])


class TestSingleTimeframeFetch:
    """Test fetching single timeframe."""

    def test_fetch_single_timeframe_success(self):
        """Test successful single timeframe fetch."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        mock_bars = create_mock_bars(num_bars=3)
        data_source.get_stream_data.return_value = mock_bars

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5", "15"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        result = service.fetch_single_timeframe("5")

        assert result is True

        # Should only call for that timeframe
        data_source.get_stream_data.assert_called_once_with(
            symbol="EURUSD",
            timeframe="5",
            nbr_bars=3,
        )

    def test_fetch_single_timeframe_not_configured(self):
        """Test fetch fails for non-configured timeframe."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        result = service.fetch_single_timeframe("15")

        assert result is False
        data_source.get_stream_data.assert_not_called()

    def test_fetch_single_timeframe_when_not_running(self):
        """Test fetch fails when service not running."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        # Don't start service
        result = service.fetch_single_timeframe("1")

        assert result is False


class TestResetLastKnownBars:
    """Test resetting last known bars."""

    def test_reset_all_timeframes(self):
        """Test resetting all timeframes."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        # Set some bars
        service.last_known_bars["1"] = create_mock_bar()
        service.last_known_bars["5"] = create_mock_bar()

        service.reset_last_known_bars()

        # Should be reset to None
        assert service.last_known_bars["1"] is None
        assert service.last_known_bars["5"] is None

    def test_reset_single_timeframe(self):
        """Test resetting single timeframe."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        # Set some bars
        bar1 = create_mock_bar(close=1.09)
        bar5 = create_mock_bar(close=1.10)
        service.last_known_bars["1"] = bar1
        service.last_known_bars["5"] = bar5

        service.reset_last_known_bars("1")

        # Only "1" should be reset
        assert service.last_known_bars["1"] is None
        assert service.last_known_bars["5"] is not None


class TestMetrics:
    """Test metrics tracking."""

    def test_metrics_track_data_fetches(self):
        """Test metrics track number of data fetches."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        mock_bars = create_mock_bars(num_bars=3)
        data_source.get_stream_data.return_value = mock_bars

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        # Fetch twice
        service.fetch_streaming_data()
        service.fetch_streaming_data()

        metrics = service.get_metrics()

        # Should track 4 fetches (2 timeframes * 2 calls)
        assert metrics["data_fetches"] == 4

    def test_metrics_track_new_candles(self):
        """Test metrics track new candles detected."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        # First fetch - new candle
        bars1 = create_mock_bars(num_bars=3, start_time=datetime.now() - timedelta(minutes=10))
        data_source.get_stream_data.return_value = bars1
        service.fetch_streaming_data()

        # Second fetch - new candle
        bars2 = create_mock_bars(num_bars=3, start_time=datetime.now() - timedelta(minutes=5))
        data_source.get_stream_data.return_value = bars2
        service.fetch_streaming_data()

        metrics = service.get_metrics()

        assert metrics["new_candles_detected"] == 2

    def test_metrics_track_fetch_errors(self):
        """Test metrics track fetch errors."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        # First call succeeds, second fails
        mock_bars = create_mock_bars(num_bars=3)
        data_source.get_stream_data.side_effect = [
            mock_bars,
            Exception("Error"),
        ]

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        service.start()

        # Two fetches
        service.fetch_streaming_data()
        service.fetch_streaming_data()

        metrics = service.get_metrics()

        assert metrics["fetch_errors"] == 1

    def test_metrics_include_timeframes_count(self):
        """Test metrics include configured timeframes count."""
        mock_bus = MockEventBus()
        data_source = Mock(spec=DataSourceManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5", "15"],
        }

        service = DataFetchingService(
            event_bus=mock_bus,
            data_source=data_source,
            config=config,
        )

        metrics = service.get_metrics()

        assert metrics["timeframes_count"] == 3
