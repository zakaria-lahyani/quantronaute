"""
Tests for IndicatorCalculationService.

These tests verify that IndicatorCalculationService correctly:
- Initializes with proper configuration
- Subscribes to NewCandleEvent
- Updates regime detection
- Calculates indicators
- Publishes IndicatorsCalculatedEvent
- Detects and publishes RegimeChangedEvent
- Handles errors gracefully
- Tracks metrics correctly
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
from datetime import datetime
from collections import deque

from app.services.indicator_calculation import IndicatorCalculationService
from app.services.base import ServiceStatus
from app.infrastructure.event_bus import EventBus
from app.events.data_events import NewCandleEvent
from app.events.indicator_events import (
    IndicatorsCalculatedEvent,
    RegimeChangedEvent,
    IndicatorCalculationErrorEvent,
)
from app.indicators.indicator_processor import IndicatorProcessor
from app.regime.regime_manager import RegimeManager
from tests.fixtures.market_data import create_mock_bar
from tests.fixtures.events import create_new_candle_event
from tests.mocks.mock_event_bus import MockEventBus


class TestIndicatorCalculationServiceInitialization:
    """Test IndicatorCalculationService initialization."""

    def test_initialization_with_valid_config(self):
        """Test service initializes correctly with valid config."""
        event_bus = EventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5", "15"],
            "track_regime_changes": True,
        }

        service = IndicatorCalculationService(
            event_bus=event_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        assert service.service_name == "IndicatorCalculationService"
        assert service.symbol == "EURUSD"
        assert service.timeframes == ["1", "5", "15"]
        assert service.track_regime_changes is True
        assert service._status == ServiceStatus.INITIALIZING

    def test_initialization_with_default_values(self):
        """Test service uses default values for optional config."""
        event_bus = EventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "GBPUSD",
            "timeframes": ["5"],
        }

        service = IndicatorCalculationService(
            event_bus=event_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        # Should use default
        assert service.track_regime_changes is True

    def test_initialization_without_config_raises_error(self):
        """Test that missing config raises ValueError."""
        event_bus = EventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        with pytest.raises(ValueError, match="requires configuration"):
            IndicatorCalculationService(
                event_bus=event_bus,
                indicator_processor=indicator_processor,
                regime_manager=regime_manager,
                config=None,
            )

    def test_initialization_without_symbol_raises_error(self):
        """Test that missing symbol raises ValueError."""
        event_bus = EventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {"timeframes": ["1", "5"]}

        with pytest.raises(ValueError, match="must include 'symbol'"):
            IndicatorCalculationService(
                event_bus=event_bus,
                indicator_processor=indicator_processor,
                regime_manager=regime_manager,
                config=config,
            )

    def test_initialization_without_timeframes_raises_error(self):
        """Test that missing timeframes raises ValueError."""
        event_bus = EventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {"symbol": "EURUSD"}

        with pytest.raises(ValueError, match="must include non-empty 'timeframes'"):
            IndicatorCalculationService(
                event_bus=event_bus,
                indicator_processor=indicator_processor,
                regime_manager=regime_manager,
                config=config,
            )

    def test_last_known_regimes_initialized_correctly(self):
        """Test that last_known_regimes dict is initialized for all timeframes."""
        event_bus = EventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5", "15"],
        }

        service = IndicatorCalculationService(
            event_bus=event_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        assert len(service.last_known_regimes) == 3
        assert "1" in service.last_known_regimes
        assert "5" in service.last_known_regimes
        assert "15" in service.last_known_regimes
        assert service.last_known_regimes["1"] is None
        assert service.last_known_regimes["5"] is None
        assert service.last_known_regimes["15"] is None


class TestIndicatorCalculationServiceLifecycle:
    """Test service lifecycle (start/stop)."""

    def test_start_subscribes_to_new_candle_event(self):
        """Test that start() subscribes to NewCandleEvent."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        # Should subscribe to NewCandleEvent
        assert len(service._subscription_ids) > 0
        assert service._status == ServiceStatus.RUNNING

    def test_stop_unsubscribes_from_events(self):
        """Test that stop() unsubscribes from events."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()
        assert len(service._subscription_ids) > 0

        service.stop()

        # Should have unsubscribed
        assert len(service._subscription_ids) == 0
        assert service._status == ServiceStatus.STOPPED

    def test_stop_clears_last_known_regimes(self):
        """Test that stop() clears last_known_regimes."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        # Set some regimes
        service.last_known_regimes["1"] = "bull_high"
        service.last_known_regimes["5"] = "bear_low"

        service.start()
        service.stop()

        # Should be cleared
        assert len(service.last_known_regimes) == 0


class TestIndicatorCalculationServiceHealthCheck:
    """Test health check functionality."""

    def test_health_check_healthy_when_running(self):
        """Test health check returns healthy when running."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        health = service.health_check()

        assert health.is_healthy is True
        assert health.status == ServiceStatus.RUNNING

    def test_health_check_unhealthy_with_many_errors(self):
        """Test health check returns unhealthy with many errors."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        # Simulate many errors
        service._metrics["calculation_errors"] = 15

        health = service.health_check()

        assert health.is_healthy is False


class TestNewCandleEventHandling:
    """Test handling of NewCandleEvent."""

    def test_processes_new_candle_for_correct_symbol(self):
        """Test service processes NewCandleEvent for correct symbol."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        # Mock regime manager to return regime data
        regime_manager.update.return_value = {
            "regime": "bull_high",
            "regime_confidence": 0.85,
            "is_transition": False,
        }

        # Mock indicator processor to return processed row
        mock_processed_row = pd.Series({"close": 1.09, "regime": "bull_high"})
        indicator_processor.process_new_row.return_value = mock_processed_row
        indicator_processor.get_recent_rows.return_value = {"1": deque([mock_processed_row])}

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        # Publish NewCandleEvent
        event = create_new_candle_event(symbol="EURUSD", timeframe="1")
        service._on_new_candle(event)

        # Should have called regime manager
        regime_manager.update.assert_called_once()

        # Should have called indicator processor
        indicator_processor.process_new_row.assert_called_once()

        # Should have published IndicatorsCalculatedEvent
        events = mock_bus.get_published_events(IndicatorsCalculatedEvent)
        assert len(events) == 1
        assert events[0].symbol == "EURUSD"
        assert events[0].timeframe == "1"

    def test_ignores_new_candle_for_different_symbol(self):
        """Test service ignores NewCandleEvent for different symbol."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        # Publish NewCandleEvent for different symbol
        event = create_new_candle_event(symbol="GBPUSD", timeframe="1")
        service._on_new_candle(event)

        # Should NOT have called regime manager or indicator processor
        regime_manager.update.assert_not_called()
        indicator_processor.process_new_row.assert_not_called()

        # Should NOT have published any events
        events = mock_bus.get_published_events(IndicatorsCalculatedEvent)
        assert len(events) == 0

    def test_ignores_new_candle_for_different_timeframe(self):
        """Test service ignores NewCandleEvent for non-configured timeframe."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        # Publish NewCandleEvent for different timeframe
        event = create_new_candle_event(symbol="EURUSD", timeframe="15")
        service._on_new_candle(event)

        # Should NOT have called regime manager or indicator processor
        regime_manager.update.assert_not_called()
        indicator_processor.process_new_row.assert_not_called()

    def test_handles_exception_during_processing(self):
        """Test service handles exception during indicator calculation."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        # Mock regime manager to raise exception
        regime_manager.update.side_effect = Exception("Calculation error")

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        # Publish NewCandleEvent
        event = create_new_candle_event(symbol="EURUSD", timeframe="1")
        service._on_new_candle(event)

        # Should have published error event
        error_events = mock_bus.get_published_events(IndicatorCalculationErrorEvent)
        assert len(error_events) == 1
        assert "Calculation error" in error_events[0].error


class TestRegimeChangeDetection:
    """Test regime change detection."""

    def test_publishes_regime_changed_event_on_regime_change(self):
        """Test service publishes RegimeChangedEvent when regime changes."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        # Mock to return processed row
        mock_processed_row = pd.Series({"close": 1.09})
        indicator_processor.process_new_row.return_value = mock_processed_row
        indicator_processor.get_recent_rows.return_value = {"1": deque([mock_processed_row])}

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
            "track_regime_changes": True,
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        # First candle - bull_high regime
        regime_manager.update.return_value = {
            "regime": "bull_high",
            "regime_confidence": 0.85,
            "is_transition": False,
        }
        event1 = create_new_candle_event(symbol="EURUSD", timeframe="1")
        service._on_new_candle(event1)

        # Second candle - bull_low regime (changed!)
        regime_manager.update.return_value = {
            "regime": "bull_low",
            "regime_confidence": 0.75,
            "is_transition": False,
        }
        event2 = create_new_candle_event(symbol="EURUSD", timeframe="1", close=1.0850)
        service._on_new_candle(event2)

        # Should have published RegimeChangedEvent
        regime_events = mock_bus.get_published_events(RegimeChangedEvent)
        assert len(regime_events) == 1
        assert regime_events[0].old_regime == "bull_high"
        assert regime_events[0].new_regime == "bull_low"
        assert regime_events[0].confidence == 0.75

    def test_does_not_publish_regime_changed_on_first_candle(self):
        """Test service does not publish RegimeChangedEvent on first candle."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        # Mock to return processed row
        mock_processed_row = pd.Series({"close": 1.09})
        indicator_processor.process_new_row.return_value = mock_processed_row
        indicator_processor.get_recent_rows.return_value = {"1": deque([mock_processed_row])}

        # Mock regime manager
        regime_manager.update.return_value = {
            "regime": "bull_high",
            "regime_confidence": 0.85,
            "is_transition": False,
        }

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
            "track_regime_changes": True,
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        # First candle
        event = create_new_candle_event(symbol="EURUSD", timeframe="1")
        service._on_new_candle(event)

        # Should NOT have published RegimeChangedEvent (no previous regime)
        regime_events = mock_bus.get_published_events(RegimeChangedEvent)
        assert len(regime_events) == 0

    def test_does_not_publish_regime_changed_when_disabled(self):
        """Test service does not publish RegimeChangedEvent when tracking disabled."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        # Mock to return processed row
        mock_processed_row = pd.Series({"close": 1.09})
        indicator_processor.process_new_row.return_value = mock_processed_row
        indicator_processor.get_recent_rows.return_value = {"1": deque([mock_processed_row])}

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
            "track_regime_changes": False,  # Disabled
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        # First candle - bull_high regime
        regime_manager.update.return_value = {
            "regime": "bull_high",
            "regime_confidence": 0.85,
            "is_transition": False,
        }
        event1 = create_new_candle_event(symbol="EURUSD", timeframe="1")
        service._on_new_candle(event1)

        # Second candle - different regime
        regime_manager.update.return_value = {
            "regime": "bull_low",
            "regime_confidence": 0.75,
            "is_transition": False,
        }
        event2 = create_new_candle_event(symbol="EURUSD", timeframe="1", close=1.0850)
        service._on_new_candle(event2)

        # Should NOT have published RegimeChangedEvent (tracking disabled)
        regime_events = mock_bus.get_published_events(RegimeChangedEvent)
        assert len(regime_events) == 0


class TestAccessorMethods:
    """Test accessor methods for recent rows and regimes."""

    def test_get_recent_rows(self):
        """Test get_recent_rows returns data from processor."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        mock_recent_rows = {"1": deque([{"close": 1.09}])}
        indicator_processor.get_recent_rows.return_value = mock_recent_rows

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        result = service.get_recent_rows()

        assert result == mock_recent_rows
        indicator_processor.get_recent_rows.assert_called_once()

    def test_get_latest_row(self):
        """Test get_latest_row returns data from processor."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        mock_row = pd.Series({"close": 1.09, "regime": "bull_high"})
        indicator_processor.get_latest_row.return_value = mock_row

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        result = service.get_latest_row("1")

        assert result.equals(mock_row)
        indicator_processor.get_latest_row.assert_called_once_with("1")

    def test_get_current_regime(self):
        """Test get_current_regime returns stored regime."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        # Set a regime
        service.last_known_regimes["1"] = "bull_high"

        result = service.get_current_regime("1")

        assert result == "bull_high"

    def test_get_all_regimes(self):
        """Test get_all_regimes returns all stored regimes."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        # Set regimes
        service.last_known_regimes["1"] = "bull_high"
        service.last_known_regimes["5"] = "bull_low"

        result = service.get_all_regimes()

        assert result == {"1": "bull_high", "5": "bull_low"}


class TestMetrics:
    """Test metrics tracking."""

    def test_metrics_track_indicators_calculated(self):
        """Test metrics track number of indicators calculated."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        # Mock returns
        regime_manager.update.return_value = {
            "regime": "bull_high",
            "regime_confidence": 0.85,
            "is_transition": False,
        }
        mock_processed_row = pd.Series({"close": 1.09})
        indicator_processor.process_new_row.return_value = mock_processed_row
        indicator_processor.get_recent_rows.return_value = {"1": deque([mock_processed_row])}

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        # Process two candles
        event1 = create_new_candle_event(symbol="EURUSD", timeframe="1")
        service._on_new_candle(event1)

        event2 = create_new_candle_event(symbol="EURUSD", timeframe="1", close=1.0850)
        service._on_new_candle(event2)

        metrics = service.get_metrics()

        assert metrics["indicators_calculated"] == 2

    def test_metrics_track_regime_changes(self):
        """Test metrics track regime changes."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        # Mock returns
        mock_processed_row = pd.Series({"close": 1.09})
        indicator_processor.process_new_row.return_value = mock_processed_row
        indicator_processor.get_recent_rows.return_value = {"1": deque([mock_processed_row])}

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1"],
            "track_regime_changes": True,
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        service.start()

        # First candle - bull_high
        regime_manager.update.return_value = {
            "regime": "bull_high",
            "regime_confidence": 0.85,
            "is_transition": False,
        }
        event1 = create_new_candle_event(symbol="EURUSD", timeframe="1")
        service._on_new_candle(event1)

        # Second candle - bull_low (changed)
        regime_manager.update.return_value = {
            "regime": "bull_low",
            "regime_confidence": 0.75,
            "is_transition": False,
        }
        event2 = create_new_candle_event(symbol="EURUSD", timeframe="1", close=1.0850)
        service._on_new_candle(event2)

        metrics = service.get_metrics()

        assert metrics["regime_changes_detected"] == 1

    def test_metrics_include_timeframes_count(self):
        """Test metrics include configured timeframes count."""
        mock_bus = MockEventBus()
        indicator_processor = Mock(spec=IndicatorProcessor)
        regime_manager = Mock(spec=RegimeManager)

        config = {
            "symbol": "EURUSD",
            "timeframes": ["1", "5", "15"],
        }

        service = IndicatorCalculationService(
            event_bus=mock_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=config,
        )

        metrics = service.get_metrics()

        assert metrics["timeframes_count"] == 3
