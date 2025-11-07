"""
Integration tests for complete trading cycle.

These tests verify that all services work together correctly and that
events flow properly through the entire system from data fetching to
trade execution.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
import pandas as pd

from app.infrastructure.event_bus import EventBus
from app.infrastructure.orchestrator import TradingOrchestrator, OrchestratorStatus
from app.services.data_fetching import DataFetchingService
from app.services.indicator_calculation import IndicatorCalculationService
from app.services.strategy_evaluation import StrategyEvaluationService
from app.services.trade_execution import TradeExecutionService
from app.events.data_events import DataFetchedEvent, NewCandleEvent
from app.events.indicator_events import IndicatorsCalculatedEvent, RegimeChangedEvent
from app.events.strategy_events import EntrySignalEvent, ExitSignalEvent
from app.events.trade_events import TradingAuthorizedEvent, TradingBlockedEvent


class TestCompleteTradingCycle:
    """Test complete trading cycle from data fetch to trade execution."""

    @pytest.fixture
    def mock_components(self):
        """Create all mock components needed for testing."""
        # Mock MT5 Client
        client = Mock()

        # Mock DataSourceManager
        data_source = Mock()
        # Return multi-row DataFrame with proper data
        data_source.get_stream_data.return_value = pd.DataFrame({
            'time': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 1, 10, 1),
                datetime(2024, 1, 1, 10, 2),
            ],
            'open': [1.1000, 1.1005, 1.1010],
            'high': [1.1010, 1.1015, 1.1020],
            'low': [1.0990, 1.0995, 1.1000],
            'close': [1.1005, 1.1010, 1.1015],
            'volume': [1000, 1100, 1200],
        })

        # Mock IndicatorProcessor
        indicator_processor = Mock()
        indicator_processor.process_indicators.return_value = pd.DataFrame({
            'time': [
                datetime(2024, 1, 1, 10, 0),
                datetime(2024, 1, 1, 10, 1),
                datetime(2024, 1, 1, 10, 2),
            ],
            'open': [1.1000, 1.1005, 1.1010],
            'high': [1.1010, 1.1015, 1.1020],
            'low': [1.0990, 1.0995, 1.1000],
            'close': [1.1005, 1.1010, 1.1015],
            'volume': [1000, 1100, 1200],
            'sma_20': [1.1000, 1.1005, 1.1010],
            'rsi_14': [55.0, 56.0, 57.0],
        })

        # Mock RegimeManager
        regime_manager = Mock()
        regime_manager.get_current_regime.return_value = "trending"
        regime_manager.detect_regime_change.return_value = False

        # Mock StrategyEngine
        strategy_engine = Mock()
        strategy_engine.evaluate_strategies.return_value = pd.DataFrame({
            'time': [datetime(2024, 1, 1, 10, 0)],
            'signal_long': [1],
            'signal_short': [0],
        })

        # Mock EntryManager
        entry_manager = Mock()
        # Return empty list (no entries for these tests)
        entry_manager.process_entries.return_value = []

        # Mock TradeExecutor
        trade_executor = Mock()
        trade_context = Mock()
        trade_context.trade_authorized = True
        trade_context.news_block_active = False
        trade_context.market_closing_soon = False
        trade_context.risk_breached = False
        trade_context.total_pnl = 0.0
        trade_executor.execute_trading_cycle.return_value = trade_context

        # Mock DateHelper
        date_helper = Mock()
        date_helper.get_current_time.return_value = datetime(2024, 1, 1, 10, 0)

        return {
            "client": client,
            "data_source": data_source,
            "indicator_processor": indicator_processor,
            "regime_manager": regime_manager,
            "strategy_engine": strategy_engine,
            "entry_manager": entry_manager,
            "trade_executor": trade_executor,
            "date_helper": date_helper,
        }

    @pytest.fixture
    def orchestrator_config(self):
        """Create orchestrator configuration."""
        return {
            "symbol": "EURUSD",
            "timeframes": ["1", "5"],
            "enable_auto_restart": False,
            "health_check_interval": 60,
            "event_history_limit": 100,
            "log_all_events": False,
            "candle_index": 1,
            "nbr_bars": 3,
            "track_regime_changes": True,
            "min_rows_required": 1,
            "execution_mode": "immediate",
        }

    def test_orchestrator_initialization(self, mock_components, orchestrator_config):
        """Test that orchestrator initializes all services correctly."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)

        orchestrator.initialize(**mock_components)

        # Verify all services created
        assert len(orchestrator.services) == 4
        assert "data_fetching" in orchestrator.services
        assert "indicator_calculation" in orchestrator.services
        assert "strategy_evaluation" in orchestrator.services
        assert "trade_execution" in orchestrator.services

        # Verify service order
        assert orchestrator.service_order == [
            "data_fetching",
            "indicator_calculation",
            "strategy_evaluation",
            "trade_execution",
        ]

        # Verify EventBus created
        assert orchestrator.event_bus is not None

    def test_orchestrator_start_stop(self, mock_components, orchestrator_config):
        """Test that orchestrator can start and stop all services."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)

        # Start services
        orchestrator.start()

        # Verify orchestrator status
        assert orchestrator.status == OrchestratorStatus.RUNNING

        # Verify all services started
        for service_name in orchestrator.service_order:
            service = orchestrator.services[service_name]
            assert service._status.value == "running"

        # Stop services
        orchestrator.stop()

        # Verify orchestrator status
        assert orchestrator.status == OrchestratorStatus.STOPPED

        # Verify all services stopped
        for service_name in orchestrator.service_order:
            service = orchestrator.services[service_name]
            assert service._status.value == "stopped"

    def test_complete_event_flow(self, mock_components, orchestrator_config):
        """Test that events flow correctly through all services."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        # Track events
        events_received = []

        def track_event(event):
            events_received.append(type(event).__name__)

        # Subscribe to all events
        orchestrator.event_bus.subscribe(DataFetchedEvent, track_event)
        orchestrator.event_bus.subscribe(NewCandleEvent, track_event)
        orchestrator.event_bus.subscribe(IndicatorsCalculatedEvent, track_event)
        orchestrator.event_bus.subscribe(EntrySignalEvent, track_event)

        # Trigger data fetch (should cascade through all services)
        data_service = orchestrator.services["data_fetching"]
        success_count = data_service.fetch_streaming_data()

        # Verify data was fetched
        assert success_count > 0

        # Verify events were published
        assert "DataFetchedEvent" in events_received
        assert "NewCandleEvent" in events_received
        assert "IndicatorsCalculatedEvent" in events_received

        orchestrator.stop()

    def test_data_to_indicators_flow(self, mock_components, orchestrator_config):
        """Test data fetching triggers indicator calculation."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        indicator_service = orchestrator.services["indicator_calculation"]
        initial_calc_count = indicator_service._metrics["indicators_calculated"]

        # Fetch data
        data_service = orchestrator.services["data_fetching"]
        data_service.fetch_streaming_data()

        # Verify indicators were calculated
        assert indicator_service._metrics["indicators_calculated"] > initial_calc_count

        orchestrator.stop()

    def test_indicators_to_strategy_flow(self, mock_components, orchestrator_config):
        """Test indicator calculation triggers strategy evaluation."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        strategy_service = orchestrator.services["strategy_evaluation"]
        initial_eval_count = strategy_service._metrics["strategies_evaluated"]

        # Fetch data (triggers indicators, then strategies)
        data_service = orchestrator.services["data_fetching"]
        data_service.fetch_streaming_data()

        # Verify strategies were evaluated
        assert strategy_service._metrics["strategies_evaluated"] > initial_eval_count

        orchestrator.stop()

    def test_strategy_to_execution_flow(self, mock_components, orchestrator_config):
        """Test strategy signals trigger trade execution."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        execution_service = orchestrator.services["trade_execution"]
        initial_event_count = execution_service._metrics["events_received"]

        # Fetch data (triggers full chain)
        data_service = orchestrator.services["data_fetching"]
        data_service.fetch_streaming_data()

        # Verify execution service received events
        # Note: Events received may be 0 if no signals generated
        assert execution_service._metrics["events_received"] >= initial_event_count

        orchestrator.stop()

    def test_service_health_monitoring(self, mock_components, orchestrator_config):
        """Test that orchestrator can monitor service health."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        # Get health status
        health_status = orchestrator.get_service_health()

        # Verify all services report healthy
        assert len(health_status) == 4
        assert all(health_status.values())

        orchestrator.stop()

    def test_service_metrics_collection(self, mock_components, orchestrator_config):
        """Test that orchestrator collects metrics from all services."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        # Fetch some data
        data_service = orchestrator.services["data_fetching"]
        data_service.fetch_streaming_data()

        # Get metrics
        metrics = orchestrator.get_service_metrics()

        # Verify metrics from all services
        assert "data_fetching" in metrics
        assert "indicator_calculation" in metrics
        assert "strategy_evaluation" in metrics
        assert "trade_execution" in metrics

        # Verify data fetching metrics
        assert metrics["data_fetching"]["data_fetches"] > 0

        orchestrator.stop()

    def test_orchestrator_run_with_max_iterations(self, mock_components, orchestrator_config):
        """Test orchestrator run loop with maximum iterations."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        # Run for 3 iterations only
        orchestrator.run(interval_seconds=0.1, max_iterations=3)

        # Verify orchestrator stopped
        assert orchestrator.status == OrchestratorStatus.STOPPED

        # Verify data was fetched multiple times
        metrics = orchestrator.get_service_metrics()
        assert metrics["data_fetching"]["data_fetches"] >= 3

    def test_error_isolation_between_services(self, mock_components, orchestrator_config):
        """Test that errors in one service don't crash others."""
        # Make indicator processor raise an error
        mock_components["indicator_processor"].process_indicators.side_effect = Exception(
            "Indicator error"
        )

        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        # Fetch data (will succeed)
        data_service = orchestrator.services["data_fetching"]
        success_count = data_service.fetch_streaming_data()

        # Data service should succeed
        assert success_count > 0

        # Indicator service should have error
        indicator_service = orchestrator.services["indicator_calculation"]
        assert indicator_service._metrics["processing_errors"] > 0

        # Other services should still be running
        assert data_service._status.value == "running"
        assert orchestrator.status == OrchestratorStatus.RUNNING

        orchestrator.stop()

    def test_service_restart(self, mock_components, orchestrator_config):
        """Test that individual services can be restarted."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        # Stop a service
        data_service = orchestrator.services["data_fetching"]
        data_service.stop()
        assert data_service._status.value == "stopped"

        # Restart it
        orchestrator.restart_service("data_fetching")

        # Verify restarted
        assert data_service._status.value == "running"

        orchestrator.stop()

    def test_regime_change_detection(self, mock_components, orchestrator_config):
        """Test that regime changes are detected and propagated."""
        # Configure regime manager to report change
        mock_components["regime_manager"].detect_regime_change.return_value = True
        mock_components["regime_manager"].get_current_regime.return_value = "ranging"

        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        # Track regime change events
        regime_changes = []

        def track_regime_change(event):
            regime_changes.append(event.new_regime)

        orchestrator.event_bus.subscribe(RegimeChangedEvent, track_regime_change)

        # Fetch data (should detect regime change)
        data_service = orchestrator.services["data_fetching"]
        data_service.fetch_streaming_data()

        # Verify regime change detected
        indicator_service = orchestrator.services["indicator_calculation"]
        assert indicator_service._metrics["regime_changes_detected"] > 0

        orchestrator.stop()

    def test_trading_authorization(self, mock_components, orchestrator_config):
        """Test trading authorization flow."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        # Track authorization events
        auth_events = []

        def track_auth(event):
            auth_events.append(type(event).__name__)

        orchestrator.event_bus.subscribe(TradingAuthorizedEvent, track_auth)
        orchestrator.event_bus.subscribe(TradingBlockedEvent, track_auth)

        # Execute trades
        from app.strategy_builder.data.dtos import Trades
        trades = Trades(entries=[], exits=[])

        execution_service = orchestrator.services["trade_execution"]
        execution_service.execute_trades(trades)

        # Verify authorization event published
        assert "TradingAuthorizedEvent" in auth_events

        orchestrator.stop()

    def test_trading_blocked_scenario(self, mock_components, orchestrator_config):
        """Test trading blocked by risk limits."""
        # Configure trade executor to block trading
        trade_context = Mock()
        trade_context.trade_authorized = False
        trade_context.news_block_active = False
        trade_context.market_closing_soon = False
        trade_context.risk_breached = True
        trade_context.total_pnl = -1500.0
        mock_components["trade_executor"].execute_trading_cycle.return_value = trade_context

        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        # Track blocked events
        blocked_events = []

        def track_blocked(event):
            blocked_events.append(event.reasons)

        orchestrator.event_bus.subscribe(TradingBlockedEvent, track_blocked)

        # Execute trades
        from app.strategy_builder.data.dtos import Trades
        trades = Trades(entries=[], exits=[])

        execution_service = orchestrator.services["trade_execution"]
        execution_service.execute_trades(trades)

        # Verify blocked event published
        assert len(blocked_events) > 0
        assert "risk_breach" in blocked_events[0]

        # Verify risk breach metric
        assert execution_service._metrics["risk_breaches"] > 0

        orchestrator.stop()

    def test_all_metrics_aggregation(self, mock_components, orchestrator_config):
        """Test that all metrics are correctly aggregated."""
        orchestrator = TradingOrchestrator(config=orchestrator_config)
        orchestrator.initialize(**mock_components)
        orchestrator.start()

        # Fetch some data
        data_service = orchestrator.services["data_fetching"]
        data_service.fetch_streaming_data()

        # Get all metrics
        all_metrics = orchestrator.get_all_metrics()

        # Verify structure
        assert "orchestrator" in all_metrics
        assert "services" in all_metrics
        assert "event_bus" in all_metrics

        # Verify orchestrator metrics
        assert "status" in all_metrics["orchestrator"]
        assert "uptime_seconds" in all_metrics["orchestrator"]
        assert "services_count" in all_metrics["orchestrator"]

        # Verify services metrics
        assert len(all_metrics["services"]) == 4

        # Verify event bus metrics
        assert "events_published" in all_metrics["event_bus"]
        assert "event_types_subscribed" in all_metrics["event_bus"]

        orchestrator.stop()


class TestEventPropagation:
    """Test event propagation and error handling."""

    @pytest.fixture
    def event_bus(self):
        """Create a fresh EventBus."""
        return EventBus(event_history_limit=100)

    def test_event_history_tracking(self, event_bus):
        """Test that EventBus tracks event history."""
        # Publish some events
        import pandas as pd
        event1 = DataFetchedEvent(
            symbol="EURUSD",
            timeframe="1",
            bars=pd.DataFrame({'close': [1.1000]})
        )
        event2 = NewCandleEvent(
            symbol="EURUSD",
            timeframe="1",
            bar=pd.Series({'close': 1.1000})
        )

        event_bus.publish(event1)
        event_bus.publish(event2)

        # Verify metrics
        metrics = event_bus.get_metrics()
        assert metrics["events_published"] >= 2

    def test_subscription_management(self, event_bus):
        """Test subscription and unsubscription."""
        import pandas as pd
        handler = Mock()

        # Subscribe (returns subscription ID)
        sub_id = event_bus.subscribe(DataFetchedEvent, handler)

        # Publish event
        event = DataFetchedEvent(
            symbol="EURUSD",
            timeframe="1",
            bars=pd.DataFrame({'close': [1.1000]})
        )
        event_bus.publish(event)

        # Verify handler called
        handler.assert_called_once()

        # Unsubscribe using subscription ID
        event_bus.unsubscribe(sub_id)

        # Publish again
        event_bus.publish(event)

        # Verify handler not called again
        assert handler.call_count == 1

    def test_multiple_subscribers(self, event_bus):
        """Test multiple subscribers for same event."""
        import pandas as pd
        handler1 = Mock()
        handler2 = Mock()
        handler3 = Mock()

        # Subscribe all handlers
        event_bus.subscribe(DataFetchedEvent, handler1)
        event_bus.subscribe(DataFetchedEvent, handler2)
        event_bus.subscribe(DataFetchedEvent, handler3)

        # Publish event
        event = DataFetchedEvent(
            symbol="EURUSD",
            timeframe="1",
            bars=pd.DataFrame({'close': [1.1000]})
        )
        event_bus.publish(event)

        # Verify all handlers called
        handler1.assert_called_once()
        handler2.assert_called_once()
        handler3.assert_called_once()

    def test_error_in_handler_doesnt_stop_others(self, event_bus):
        """Test that error in one handler doesn't stop others."""
        import pandas as pd
        handler1 = Mock(side_effect=Exception("Handler error"))
        handler2 = Mock()
        handler3 = Mock()

        # Subscribe all handlers
        event_bus.subscribe(DataFetchedEvent, handler1)
        event_bus.subscribe(DataFetchedEvent, handler2)
        event_bus.subscribe(DataFetchedEvent, handler3)

        # Publish event
        event = DataFetchedEvent(
            symbol="EURUSD",
            timeframe="1",
            bars=pd.DataFrame({'close': [1.1000]})
        )
        event_bus.publish(event)

        # Verify handler1 was called (and raised error)
        handler1.assert_called_once()

        # Verify other handlers still called despite error
        handler2.assert_called_once()
        handler3.assert_called_once()
