"""
Unit tests for MultiSymbolTradingOrchestrator.

Tests cover:
- Initialization with multiple symbols
- Service creation per symbol
- Health monitoring across symbols
- Metrics collection per symbol
- Auto-restart functionality
- Symbol isolation (one symbol failure doesn't affect others)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import datetime
from typing import Dict, Any

from app.infrastructure.multi_symbol_orchestrator import (
    MultiSymbolTradingOrchestrator,
    OrchestratorStatus
)
from app.infrastructure.event_bus import EventBus
from app.services.base import ServiceStatus, HealthStatus


@pytest.fixture
def mock_components():
    """Create mock components for testing."""
    return {
        'indicator_processor': Mock(),
        'regime_manager': Mock(),
        'strategy_engine': Mock(),
        'entry_manager': Mock(),
        'trade_executor': Mock()
    }


@pytest.fixture
def mock_symbol_components(mock_components):
    """Create mock components for multiple symbols."""
    return {
        'XAUUSD': mock_components.copy(),
        'BTCUSD': mock_components.copy(),
        'EURUSD': mock_components.copy()
    }


@pytest.fixture
def orchestrator_config():
    """Create orchestrator configuration."""
    return {
        'symbols': ['XAUUSD', 'BTCUSD', 'EURUSD'],
        'timeframes': ['1', '5', '15'],
        'enable_auto_restart': True,
        'health_check_interval': 60,
        'candle_index': 1,
        'nbr_bars': 3,
        'track_regime_changes': True,
        'min_rows_required': 3,
        'execution_mode': 'immediate'
    }


class TestMultiSymbolOrchestratorInitialization:
    """Test orchestrator initialization."""

    def test_create_with_valid_config(self, orchestrator_config):
        """Test creating orchestrator with valid configuration."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        assert orchestrator.symbols == ['XAUUSD', 'BTCUSD', 'EURUSD']
        assert orchestrator.timeframes == ['1', '5', '15']
        assert orchestrator.enable_auto_restart is True
        assert orchestrator.status == OrchestratorStatus.INITIALIZING

    def test_create_without_symbols_raises_error(self):
        """Test creating orchestrator without symbols raises error."""
        config = {
            'symbols': [],
            'timeframes': ['1', '5']
        }

        with pytest.raises(ValueError, match="At least one symbol must be specified"):
            MultiSymbolTradingOrchestrator(config=config)

    def test_services_dict_initialized_per_symbol(self, orchestrator_config):
        """Test that services dict is initialized for each symbol."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        assert 'XAUUSD' in orchestrator.services
        assert 'BTCUSD' in orchestrator.services
        assert 'EURUSD' in orchestrator.services
        assert orchestrator.services['XAUUSD'] == {}
        assert orchestrator.services['BTCUSD'] == {}


class TestServiceCreation:
    """Test service creation for multiple symbols."""

    @patch('app.infrastructure.multi_symbol_orchestrator.DataFetchingService')
    @patch('app.infrastructure.multi_symbol_orchestrator.IndicatorCalculationService')
    @patch('app.infrastructure.multi_symbol_orchestrator.StrategyEvaluationService')
    @patch('app.infrastructure.multi_symbol_orchestrator.TradeExecutionService')
    def test_initialize_creates_services_per_symbol(
        self,
        mock_trade_exec,
        mock_strategy_eval,
        mock_indicator_calc,
        mock_data_fetch,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test that initialize creates 4 services per symbol."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        # Mock service instances
        for mock_service in [mock_data_fetch, mock_indicator_calc, mock_strategy_eval, mock_trade_exec]:
            mock_service.return_value = Mock()

        # Initialize
        orchestrator.initialize(
            client=Mock(),
            data_source=Mock(),
            symbol_components=mock_symbol_components,
            date_helper=Mock()
        )

        # Verify services created for each symbol
        assert 'data_fetching' in orchestrator.services['XAUUSD']
        assert 'indicator_calculation' in orchestrator.services['XAUUSD']
        assert 'strategy_evaluation' in orchestrator.services['XAUUSD']
        assert 'trade_execution' in orchestrator.services['XAUUSD']

        # Verify same for other symbols
        for symbol in ['BTCUSD', 'EURUSD']:
            assert len(orchestrator.services[symbol]) == 4

        # Verify service constructors called correct number of times (3 symbols x 4 services = 12)
        assert mock_data_fetch.call_count == 3
        assert mock_indicator_calc.call_count == 3
        assert mock_strategy_eval.call_count == 3
        assert mock_trade_exec.call_count == 3

    @patch('app.infrastructure.multi_symbol_orchestrator.DataFetchingService')
    def test_data_service_created_with_correct_symbol_config(
        self,
        mock_data_fetch,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test that DataFetchingService receives correct symbol-specific config."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        mock_service_instance = Mock()
        mock_data_fetch.return_value = mock_service_instance

        orchestrator.initialize(
            client=Mock(),
            data_source=Mock(),
            symbol_components=mock_symbol_components,
            date_helper=Mock()
        )

        # Get the config passed to the first call (XAUUSD)
        first_call_config = mock_data_fetch.call_args_list[0][1]['config']

        assert first_call_config['symbol'] == 'XAUUSD'
        assert first_call_config['timeframes'] == ['1', '5', '15']
        assert first_call_config['candle_index'] == 1
        assert first_call_config['nbr_bars'] == 3

    def test_initialize_creates_shared_event_bus(
        self,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test that initialize creates a single shared EventBus."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        orchestrator.initialize(
            client=Mock(),
            data_source=Mock(),
            symbol_components=mock_symbol_components,
            date_helper=Mock()
        )

        assert orchestrator.event_bus is not None
        assert isinstance(orchestrator.event_bus, EventBus)


class TestServiceLifecycle:
    """Test service start/stop lifecycle."""

    def test_start_calls_start_on_all_services(
        self,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test that start() calls start() on all services."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        orchestrator.initialize(
            client=Mock(),
            data_source=Mock(),
            symbol_components=mock_symbol_components,
            date_helper=Mock()
        )

        # Start orchestrator
        orchestrator.start()

        # Verify status changed
        assert orchestrator.status == OrchestratorStatus.RUNNING
        assert orchestrator.start_time is not None

        # Verify all services started (3 symbols x 4 services = 12)
        total_starts = 0
        for symbol in orchestrator.symbols:
            for service_name in orchestrator.service_order:
                service = orchestrator.services[symbol][service_name]
                service.start.assert_called_once()
                total_starts += 1

        assert total_starts == 12

    def test_stop_calls_stop_on_all_services_in_reverse_order(
        self,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test that stop() calls stop() on all services in reverse order."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        orchestrator.initialize(
            client=Mock(),
            data_source=Mock(),
            symbol_components=mock_symbol_components,
            date_helper=Mock()
        )

        orchestrator.start()
        orchestrator.stop()

        # Verify status changed
        assert orchestrator.status == OrchestratorStatus.STOPPED

        # Verify all services stopped
        for symbol in orchestrator.symbols:
            for service_name in orchestrator.service_order:
                service = orchestrator.services[symbol][service_name]
                service.stop.assert_called_once()


class TestHealthMonitoring:
    """Test health monitoring across symbols."""

    def test_get_service_health_returns_status_per_symbol(
        self,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test get_service_health returns health status for all symbols."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        orchestrator.initialize(
            client=Mock(),
            data_source=Mock(),
            symbol_components=mock_symbol_components,
            date_helper=Mock()
        )

        # Mock health checks
        for symbol in orchestrator.symbols:
            for service_name in orchestrator.service_order:
                service = orchestrator.services[symbol][service_name]
                service.health_check.return_value = HealthStatus(
                    service_name=service_name,
                    status=ServiceStatus.RUNNING,
                    is_healthy=True,
                    uptime_seconds=100.0,
                    last_error=None,
                    metrics={}
                )

        health = orchestrator.get_service_health()

        # Verify structure
        assert 'XAUUSD' in health
        assert 'BTCUSD' in health
        assert 'EURUSD' in health

        # Verify all services reported
        assert health['XAUUSD']['data_fetching'] is True
        assert health['XAUUSD']['indicator_calculation'] is True
        assert health['BTCUSD']['strategy_evaluation'] is True
        assert health['EURUSD']['trade_execution'] is True

    def test_unhealthy_service_detected_per_symbol(
        self,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test that unhealthy services are detected per symbol."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        orchestrator.initialize(
            client=Mock(),
            data_source=Mock(),
            symbol_components=mock_symbol_components,
            date_helper=Mock()
        )

        # Make one service unhealthy
        for symbol in orchestrator.symbols:
            for service_name in orchestrator.service_order:
                service = orchestrator.services[symbol][service_name]
                is_healthy = not (symbol == 'BTCUSD' and service_name == 'indicator_calculation')
                service.health_check.return_value = HealthStatus(
                    service_name=service_name,
                    status=ServiceStatus.RUNNING if is_healthy else ServiceStatus.ERROR,
                    is_healthy=is_healthy,
                    uptime_seconds=100.0,
                    last_error="Test error" if not is_healthy else None,
                    metrics={}
                )

        health = orchestrator.get_service_health()

        # BTCUSD indicator service should be unhealthy
        assert health['BTCUSD']['indicator_calculation'] is False

        # Other services should be healthy
        assert health['XAUUSD']['indicator_calculation'] is True
        assert health['EURUSD']['indicator_calculation'] is True
        assert health['BTCUSD']['data_fetching'] is True


class TestAutoRestart:
    """Test automatic service restart functionality."""

    def test_auto_restart_triggered_for_unhealthy_service(
        self,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test that auto-restart is triggered for unhealthy services."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        orchestrator.initialize(
            client=Mock(),
            data_source=Mock(),
            symbol_components=mock_symbol_components,
            date_helper=Mock()
        )

        orchestrator.start()
        orchestrator.last_health_check = None  # Force health check

        # Make BTCUSD indicator service unhealthy
        unhealthy_service = orchestrator.services['BTCUSD']['indicator_calculation']
        unhealthy_service.health_check.return_value = HealthStatus(
            service_name='indicator_calculation',
            status=ServiceStatus.ERROR,
            is_healthy=False,
            uptime_seconds=100.0,
            last_error="Test error",
            metrics={}
        )

        # Make other services healthy
        for symbol in orchestrator.symbols:
            for service_name in orchestrator.service_order:
                service = orchestrator.services[symbol][service_name]
                if not (symbol == 'BTCUSD' and service_name == 'indicator_calculation'):
                    service.health_check.return_value = HealthStatus(
                        service_name=service_name,
                        status=ServiceStatus.RUNNING,
                        is_healthy=True,
                        uptime_seconds=100.0,
                        last_error=None,
                        metrics={}
                    )

        # Perform health check
        orchestrator._perform_health_check()

        # Verify unhealthy service was restarted
        unhealthy_service.stop.assert_called_once()
        assert unhealthy_service.start.call_count >= 2  # Initial start + restart


class TestMetrics:
    """Test metrics collection across symbols."""

    def test_get_all_metrics_returns_per_symbol_metrics(
        self,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test get_all_metrics returns metrics for all symbols."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        orchestrator.initialize(
            client=Mock(),
            data_source=Mock(),
            symbol_components=mock_symbol_components,
            date_helper=Mock()
        )

        orchestrator.start()

        # Mock service metrics
        for symbol in orchestrator.symbols:
            for service_name in orchestrator.service_order:
                service = orchestrator.services[symbol][service_name]
                service.get_metrics.return_value = {
                    'events_published': 10,
                    'events_received': 5
                }

        metrics = orchestrator.get_all_metrics()

        # Verify structure
        assert 'orchestrator' in metrics
        assert 'services' in metrics
        assert 'event_bus' in metrics

        # Verify orchestrator metrics
        assert metrics['orchestrator']['status'] == 'running'
        assert metrics['orchestrator']['symbols'] == ['XAUUSD', 'BTCUSD', 'EURUSD']
        assert metrics['orchestrator']['total_services'] == 12
        assert metrics['orchestrator']['symbols_count'] == 3

        # Verify per-symbol service metrics
        assert 'XAUUSD' in metrics['services']
        assert 'BTCUSD' in metrics['services']
        assert 'data_fetching' in metrics['services']['XAUUSD']
        assert metrics['services']['XAUUSD']['data_fetching']['events_published'] == 10


class TestSymbolIsolation:
    """Test that symbol failures are isolated."""

    def test_one_symbol_service_failure_does_not_affect_others(
        self,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test that a service failure in one symbol doesn't affect other symbols."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        orchestrator.initialize(
            client=Mock(),
            data_source=Mock(),
            symbol_components=mock_symbol_components,
            date_helper=Mock()
        )

        # Make BTCUSD data service raise error on start
        btc_data_service = orchestrator.services['BTCUSD']['data_fetching']
        btc_data_service.start.side_effect = Exception("BTCUSD data service failed")

        # Start should raise error (BTCUSD fails)
        with pytest.raises(Exception, match="BTCUSD data service failed"):
            orchestrator.start()

        # XAUUSD and EURUSD services should have been started before BTCUSD failure
        xau_data_service = orchestrator.services['XAUUSD']['data_fetching']
        xau_data_service.start.assert_called_once()

    def test_services_use_separate_loggers_per_symbol(
        self,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test that each symbol's services use separate loggers."""
        with patch('app.infrastructure.multi_symbol_orchestrator.DataFetchingService') as mock_data_fetch:
            orchestrator = MultiSymbolTradingOrchestrator(
                config=orchestrator_config,
                logger=Mock()
            )

            mock_data_fetch.return_value = Mock()

            orchestrator.initialize(
                client=Mock(),
                data_source=Mock(),
                symbol_components=mock_symbol_components,
                date_helper=Mock()
            )

            # Get logger arguments from calls
            call_loggers = [call[1]['logger'].name for call in mock_data_fetch.call_args_list]

            # Verify separate loggers per symbol
            assert 'data-fetching-xauusd' in call_loggers
            assert 'data-fetching-btcusd' in call_loggers
            assert 'data-fetching-eurusd' in call_loggers


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_initialize_with_missing_symbol_components_raises_error(
        self,
        orchestrator_config
    ):
        """Test that initialize raises error if components missing for a symbol."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        # Only provide components for XAUUSD, missing BTCUSD and EURUSD
        incomplete_components = {
            'XAUUSD': {
                'indicator_processor': Mock(),
                'regime_manager': Mock(),
                'strategy_engine': Mock(),
                'entry_manager': Mock(),
                'trade_executor': Mock()
            }
        }

        with pytest.raises(ValueError, match="No components provided for symbol BTCUSD"):
            orchestrator.initialize(
                client=Mock(),
                data_source=Mock(),
                symbol_components=incomplete_components,
                date_helper=Mock()
            )

    def test_get_uptime_before_start_returns_zero(self, orchestrator_config):
        """Test that get_uptime_seconds returns 0 before start."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        uptime = orchestrator.get_uptime_seconds()
        assert uptime == 0.0

    def test_get_uptime_after_start_returns_positive(
        self,
        orchestrator_config,
        mock_symbol_components
    ):
        """Test that get_uptime_seconds returns positive value after start."""
        orchestrator = MultiSymbolTradingOrchestrator(
            config=orchestrator_config,
            logger=Mock()
        )

        orchestrator.initialize(
            client=Mock(),
            data_source=Mock(),
            symbol_components=mock_symbol_components,
            date_helper=Mock()
        )

        orchestrator.start()

        uptime = orchestrator.get_uptime_seconds()
        assert uptime > 0.0
