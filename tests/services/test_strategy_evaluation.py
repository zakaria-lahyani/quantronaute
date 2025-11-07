"""
Tests for StrategyEvaluationService.

These tests verify that StrategyEvaluationService correctly:
- Initializes with proper configuration
- Subscribes to IndicatorsCalculatedEvent
- Evaluates strategies with enriched data
- Generates entry and exit signals
- Publishes EntrySignalEvent and ExitSignalEvent
- Handles errors gracefully
- Tracks metrics correctly
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
from datetime import datetime
from collections import deque

from app.services.strategy_evaluation import StrategyEvaluationService
from app.services.base import ServiceStatus
from app.infrastructure.event_bus import EventBus
from app.events.indicator_events import IndicatorsCalculatedEvent
from app.events.strategy_events import (
    EntrySignalEvent,
    ExitSignalEvent,
    StrategyEvaluationErrorEvent,
)
from tests.fixtures.events import create_indicators_calculated_event
from tests.mocks.mock_event_bus import MockEventBus


class TestStrategyEvaluationServiceInitialization:
    """Test StrategyEvaluationService initialization."""

    def test_initialization_with_valid_config(self):
        """Test service initializes correctly with valid config."""
        event_bus = EventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        config = {
            "symbol": "EURUSD",
            "min_rows_required": 3,
        }

        service = StrategyEvaluationService(
            event_bus=event_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        assert service.service_name == "StrategyEvaluationService"
        assert service.symbol == "EURUSD"
        assert service.min_rows_required == 3
        assert service._status == ServiceStatus.INITIALIZING

    def test_initialization_with_default_values(self):
        """Test service uses default values for optional config."""
        event_bus = EventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        config = {
            "symbol": "GBPUSD",
        }

        service = StrategyEvaluationService(
            event_bus=event_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        # Should use default
        assert service.min_rows_required == 3

    def test_initialization_without_config_raises_error(self):
        """Test that missing config raises ValueError."""
        event_bus = EventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        with pytest.raises(ValueError, match="requires configuration"):
            StrategyEvaluationService(
                event_bus=event_bus,
                strategy_engine=strategy_engine,
                entry_manager=entry_manager,
                config=None,
            )

    def test_initialization_without_symbol_raises_error(self):
        """Test that missing symbol raises ValueError."""
        event_bus = EventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        config = {"min_rows_required": 5}

        with pytest.raises(ValueError, match="must include 'symbol'"):
            StrategyEvaluationService(
                event_bus=event_bus,
                strategy_engine=strategy_engine,
                entry_manager=entry_manager,
                config=config,
            )


class TestStrategyEvaluationServiceLifecycle:
    """Test service lifecycle (start/stop)."""

    def test_start_subscribes_to_indicators_calculated_event(self):
        """Test that start() subscribes to IndicatorsCalculatedEvent."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        config = {
            "symbol": "EURUSD",
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Should subscribe to IndicatorsCalculatedEvent
        assert len(service._subscription_ids) > 0
        assert service._status == ServiceStatus.RUNNING

    def test_stop_unsubscribes_from_events(self):
        """Test that stop() unsubscribes from events."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        config = {
            "symbol": "EURUSD",
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()
        assert len(service._subscription_ids) > 0

        service.stop()

        # Should have unsubscribed
        assert len(service._subscription_ids) == 0
        assert service._status == ServiceStatus.STOPPED


class TestStrategyEvaluationServiceHealthCheck:
    """Test health check functionality."""

    def test_health_check_healthy_when_running(self):
        """Test health check returns healthy when running."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        config = {
            "symbol": "EURUSD",
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        health = service.health_check()

        assert health.is_healthy is True
        assert health.status == ServiceStatus.RUNNING

    def test_health_check_unhealthy_with_many_errors(self):
        """Test health check returns unhealthy with many errors."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        config = {
            "symbol": "EURUSD",
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Simulate many errors
        service._metrics["evaluation_errors"] = 15

        health = service.health_check()

        assert health.is_healthy is False


class TestIndicatorsCalculatedEventHandling:
    """Test handling of IndicatorsCalculatedEvent."""

    def test_processes_indicators_calculated_for_correct_symbol(self):
        """Test service processes IndicatorsCalculatedEvent for correct symbol."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        # Mock strategy engine to return evaluation results
        mock_eval_result = Mock()
        mock_eval_result.strategies = {"test_strategy": Mock()}
        strategy_engine.evaluate.return_value = mock_eval_result

        # Mock entry manager to return trades
        mock_trades = Mock()
        mock_trades.entries = []
        mock_trades.exits = []
        entry_manager.manage_trades.return_value = mock_trades

        config = {
            "symbol": "EURUSD",
            "min_rows_required": 1,  # Lower threshold for testing
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Create event with sufficient data
        recent_rows = {
            "1": deque([
                pd.Series({"close": 1.09, "regime": "bull_high"}),
                pd.Series({"close": 1.091, "regime": "bull_high"}),
            ])
        }
        event = create_indicators_calculated_event(symbol="EURUSD", timeframe="1")
        event = IndicatorsCalculatedEvent(
            symbol="EURUSD",
            timeframe="1",
            enriched_data={"regime": "bull_high"},
            recent_rows=recent_rows,
        )

        service._on_indicators_calculated(event)

        # Should have called strategy engine
        strategy_engine.evaluate.assert_called_once_with(recent_rows)

        # Should have called entry manager
        entry_manager.manage_trades.assert_called_once()

    def test_ignores_indicators_calculated_for_different_symbol(self):
        """Test service ignores IndicatorsCalculatedEvent for different symbol."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        config = {
            "symbol": "EURUSD",
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Create event for different symbol
        event = create_indicators_calculated_event(symbol="GBPUSD", timeframe="1")

        service._on_indicators_calculated(event)

        # Should NOT have called strategy engine or entry manager
        strategy_engine.evaluate.assert_not_called()
        entry_manager.manage_trades.assert_not_called()

    def test_skips_evaluation_with_insufficient_data(self):
        """Test service skips evaluation when insufficient data."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        config = {
            "symbol": "EURUSD",
            "min_rows_required": 5,  # Require 5 rows
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Create event with insufficient data (only 2 rows)
        recent_rows = {
            "1": deque([
                pd.Series({"close": 1.09}),
                pd.Series({"close": 1.091}),
            ])
        }
        event = IndicatorsCalculatedEvent(
            symbol="EURUSD",
            timeframe="1",
            enriched_data={"regime": "bull_high"},
            recent_rows=recent_rows,
        )

        service._on_indicators_calculated(event)

        # Should NOT have called strategy engine or entry manager
        strategy_engine.evaluate.assert_not_called()
        entry_manager.manage_trades.assert_not_called()

    def test_handles_exception_during_evaluation(self):
        """Test service handles exception during strategy evaluation."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        # Mock strategy engine to raise exception
        strategy_engine.evaluate.side_effect = Exception("Evaluation error")

        config = {
            "symbol": "EURUSD",
            "min_rows_required": 1,
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Create event with sufficient data
        recent_rows = {
            "1": deque([pd.Series({"close": 1.09})])
        }
        event = IndicatorsCalculatedEvent(
            symbol="EURUSD",
            timeframe="1",
            enriched_data={"regime": "bull_high"},
            recent_rows=recent_rows,
        )

        service._on_indicators_calculated(event)

        # Should have published error event
        error_events = mock_bus.get_published_events(StrategyEvaluationErrorEvent)
        assert len(error_events) == 1
        assert "Evaluation error" in error_events[0].error


class TestSignalGeneration:
    """Test entry and exit signal generation."""

    def test_publishes_entry_signal_for_long_entry(self):
        """Test service publishes EntrySignalEvent for long entry."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        # Mock strategy evaluation result
        mock_eval_result = Mock()
        mock_eval_result.strategies = {"test_strategy": Mock()}
        strategy_engine.evaluate.return_value = mock_eval_result

        # Mock entry decision for long
        mock_entry = Mock()
        mock_entry.strategy_name = "test_strategy"
        mock_entry.symbol = "EURUSD"
        mock_entry.direction = "long"
        mock_entry.entry_price = 1.0900

        mock_trades = Mock()
        mock_trades.entries = [mock_entry]
        mock_trades.exits = []
        entry_manager.manage_trades.return_value = mock_trades

        config = {
            "symbol": "EURUSD",
            "min_rows_required": 1,
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Trigger evaluation
        recent_rows = {"1": deque([pd.Series({"close": 1.09})])}
        event = IndicatorsCalculatedEvent(
            symbol="EURUSD",
            timeframe="1",
            enriched_data={},
            recent_rows=recent_rows,
        )
        service._on_indicators_calculated(event)

        # Should have published EntrySignalEvent
        entry_events = mock_bus.get_published_events(EntrySignalEvent)
        assert len(entry_events) == 1
        assert entry_events[0].strategy_name == "test_strategy"
        assert entry_events[0].symbol == "EURUSD"
        assert entry_events[0].direction == "long"
        assert entry_events[0].entry_price == 1.0900

    def test_publishes_entry_signal_for_short_entry(self):
        """Test service publishes EntrySignalEvent for short entry."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        # Mock strategy evaluation result
        mock_eval_result = Mock()
        mock_eval_result.strategies = {"test_strategy": Mock()}
        strategy_engine.evaluate.return_value = mock_eval_result

        # Mock entry decision for short
        mock_entry = Mock()
        mock_entry.strategy_name = "test_strategy"
        mock_entry.symbol = "EURUSD"
        mock_entry.direction = "short"
        mock_entry.entry_price = 1.0850

        mock_trades = Mock()
        mock_trades.entries = [mock_entry]
        mock_trades.exits = []
        entry_manager.manage_trades.return_value = mock_trades

        config = {
            "symbol": "EURUSD",
            "min_rows_required": 1,
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Trigger evaluation
        recent_rows = {"1": deque([pd.Series({"close": 1.085})])}
        event = IndicatorsCalculatedEvent(
            symbol="EURUSD",
            timeframe="1",
            enriched_data={},
            recent_rows=recent_rows,
        )
        service._on_indicators_calculated(event)

        # Should have published EntrySignalEvent
        entry_events = mock_bus.get_published_events(EntrySignalEvent)
        assert len(entry_events) == 1
        assert entry_events[0].direction == "short"

    def test_publishes_exit_signal(self):
        """Test service publishes ExitSignalEvent."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        # Mock strategy evaluation result
        mock_eval_result = Mock()
        mock_eval_result.strategies = {"test_strategy": Mock()}
        strategy_engine.evaluate.return_value = mock_eval_result

        # Mock exit decision
        mock_exit = Mock()
        mock_exit.strategy_name = "test_strategy"
        mock_exit.symbol = "EURUSD"
        mock_exit.direction = "long"

        mock_trades = Mock()
        mock_trades.entries = []
        mock_trades.exits = [mock_exit]
        entry_manager.manage_trades.return_value = mock_trades

        config = {
            "symbol": "EURUSD",
            "min_rows_required": 1,
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Trigger evaluation
        recent_rows = {"1": deque([pd.Series({"close": 1.09})])}
        event = IndicatorsCalculatedEvent(
            symbol="EURUSD",
            timeframe="1",
            enriched_data={},
            recent_rows=recent_rows,
        )
        service._on_indicators_calculated(event)

        # Should have published ExitSignalEvent
        exit_events = mock_bus.get_published_events(ExitSignalEvent)
        assert len(exit_events) == 1
        assert exit_events[0].strategy_name == "test_strategy"
        assert exit_events[0].symbol == "EURUSD"
        assert exit_events[0].direction == "long"
        assert exit_events[0].reason == "signal"

    def test_publishes_multiple_signals(self):
        """Test service publishes multiple entry and exit signals."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        # Mock strategy evaluation result
        mock_eval_result = Mock()
        mock_eval_result.strategies = {"strategy1": Mock(), "strategy2": Mock()}
        strategy_engine.evaluate.return_value = mock_eval_result

        # Mock multiple entries and exits
        mock_entry1 = Mock()
        mock_entry1.strategy_name = "strategy1"
        mock_entry1.symbol = "EURUSD"
        mock_entry1.direction = "long"
        mock_entry1.entry_price = 1.09

        mock_entry2 = Mock()
        mock_entry2.strategy_name = "strategy2"
        mock_entry2.symbol = "EURUSD"
        mock_entry2.direction = "short"
        mock_entry2.entry_price = 1.085

        mock_exit = Mock()
        mock_exit.strategy_name = "strategy1"
        mock_exit.symbol = "EURUSD"
        mock_exit.direction = "long"

        mock_trades = Mock()
        mock_trades.entries = [mock_entry1, mock_entry2]
        mock_trades.exits = [mock_exit]
        entry_manager.manage_trades.return_value = mock_trades

        config = {
            "symbol": "EURUSD",
            "min_rows_required": 1,
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Trigger evaluation
        recent_rows = {"1": deque([pd.Series({"close": 1.09})])}
        event = IndicatorsCalculatedEvent(
            symbol="EURUSD",
            timeframe="1",
            enriched_data={},
            recent_rows=recent_rows,
        )
        service._on_indicators_calculated(event)

        # Should have published 2 entry signals and 1 exit signal
        entry_events = mock_bus.get_published_events(EntrySignalEvent)
        exit_events = mock_bus.get_published_events(ExitSignalEvent)

        assert len(entry_events) == 2
        assert len(exit_events) == 1


class TestAccessorMethods:
    """Test accessor methods for strategies."""

    def test_get_available_strategies(self):
        """Test get_available_strategies returns list from engine."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        strategy_engine.list_available_strategies.return_value = [
            "strategy1", "strategy2", "strategy3"
        ]

        config = {
            "symbol": "EURUSD",
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        result = service.get_available_strategies()

        assert result == ["strategy1", "strategy2", "strategy3"]
        strategy_engine.list_available_strategies.assert_called_once()

    def test_get_strategy_info(self):
        """Test get_strategy_info returns info from engine."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        mock_strategy_info = {"name": "test_strategy", "timeframes": ["1", "5"]}
        strategy_engine.get_strategy_info.return_value = mock_strategy_info

        config = {
            "symbol": "EURUSD",
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        result = service.get_strategy_info("test_strategy")

        assert result == mock_strategy_info
        strategy_engine.get_strategy_info.assert_called_once_with("test_strategy")

    def test_get_strategy_info_handles_exception(self):
        """Test get_strategy_info handles exception gracefully."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        strategy_engine.get_strategy_info.side_effect = Exception("Strategy not found")

        config = {
            "symbol": "EURUSD",
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        result = service.get_strategy_info("unknown_strategy")

        assert result is None


class TestMetrics:
    """Test metrics tracking."""

    def test_metrics_track_strategies_evaluated(self):
        """Test metrics track number of strategies evaluated."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        # Mock returns
        mock_eval_result = Mock()
        mock_eval_result.strategies = {"test_strategy": Mock()}
        strategy_engine.evaluate.return_value = mock_eval_result

        mock_trades = Mock()
        mock_trades.entries = []
        mock_trades.exits = []
        entry_manager.manage_trades.return_value = mock_trades

        config = {
            "symbol": "EURUSD",
            "min_rows_required": 1,
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Trigger evaluation twice
        recent_rows = {"1": deque([pd.Series({"close": 1.09})])}
        event = IndicatorsCalculatedEvent(
            symbol="EURUSD",
            timeframe="1",
            enriched_data={},
            recent_rows=recent_rows,
        )

        service._on_indicators_calculated(event)
        service._on_indicators_calculated(event)

        metrics = service.get_metrics()

        assert metrics["strategies_evaluated"] == 2

    def test_metrics_track_entry_signals(self):
        """Test metrics track entry signals generated."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        # Mock returns
        mock_eval_result = Mock()
        mock_eval_result.strategies = {"test_strategy": Mock()}
        strategy_engine.evaluate.return_value = mock_eval_result

        mock_entry = Mock()
        mock_entry.strategy_name = "test_strategy"
        mock_entry.symbol = "EURUSD"
        mock_entry.direction = "long"
        mock_entry.entry_price = 1.09

        mock_trades = Mock()
        mock_trades.entries = [mock_entry]
        mock_trades.exits = []
        entry_manager.manage_trades.return_value = mock_trades

        config = {
            "symbol": "EURUSD",
            "min_rows_required": 1,
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Trigger evaluation twice
        recent_rows = {"1": deque([pd.Series({"close": 1.09})])}
        event = IndicatorsCalculatedEvent(
            symbol="EURUSD",
            timeframe="1",
            enriched_data={},
            recent_rows=recent_rows,
        )

        service._on_indicators_calculated(event)
        service._on_indicators_calculated(event)

        metrics = service.get_metrics()

        assert metrics["entry_signals_generated"] == 2

    def test_metrics_track_exit_signals(self):
        """Test metrics track exit signals generated."""
        mock_bus = MockEventBus()
        strategy_engine = Mock()
        entry_manager = Mock()

        # Mock returns
        mock_eval_result = Mock()
        mock_eval_result.strategies = {"test_strategy": Mock()}
        strategy_engine.evaluate.return_value = mock_eval_result

        mock_exit = Mock()
        mock_exit.strategy_name = "test_strategy"
        mock_exit.symbol = "EURUSD"
        mock_exit.direction = "long"

        mock_trades = Mock()
        mock_trades.entries = []
        mock_trades.exits = [mock_exit]
        entry_manager.manage_trades.return_value = mock_trades

        config = {
            "symbol": "EURUSD",
            "min_rows_required": 1,
        }

        service = StrategyEvaluationService(
            event_bus=mock_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config=config,
        )

        service.start()

        # Trigger evaluation twice
        recent_rows = {"1": deque([pd.Series({"close": 1.09})])}
        event = IndicatorsCalculatedEvent(
            symbol="EURUSD",
            timeframe="1",
            enriched_data={},
            recent_rows=recent_rows,
        )

        service._on_indicators_calculated(event)
        service._on_indicators_calculated(event)

        metrics = service.get_metrics()

        assert metrics["exit_signals_generated"] == 2
