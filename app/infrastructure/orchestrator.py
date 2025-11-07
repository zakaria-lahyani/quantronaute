"""
Trading Orchestrator.

This orchestrator manages the lifecycle of all trading services and coordinates
their operation. It's responsible for:
- Initializing all services in correct order
- Starting and stopping services gracefully
- Health monitoring and service restart
- Metrics collection and reporting
- Configuration management
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from app.infrastructure.event_bus import EventBus
from app.services.base import EventDrivenService, ServiceStatus, HealthStatus
from app.infrastructure.config import SystemConfig, ConfigLoader


class OrchestratorStatus(Enum):
    """Orchestrator status enumeration."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class TradingOrchestrator:
    """
    Orchestrates the trading system by managing service lifecycle.

    The orchestrator is responsible for:
    - Service initialization with dependency injection
    - Service startup in correct order
    - Health monitoring for all services
    - Graceful shutdown coordination
    - Service restart on failures (optional)
    - Metrics aggregation

    Example:
        ```python
        # Create orchestrator with configuration
        orchestrator = TradingOrchestrator(config={
            "symbol": "EURUSD",
            "timeframes": ["1", "5", "15"],
            "enable_auto_restart": True
        })

        # Initialize components
        orchestrator.initialize(
            client=mt5_client,
            data_source=data_source,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            trade_executor=trade_executor,
            date_helper=date_helper
        )

        # Start trading system
        orchestrator.start()

        # Run trading loop
        try:
            orchestrator.run(interval_seconds=5)
        finally:
            orchestrator.stop()
        ```
    """

    def __init__(
        self,
        config: Dict[str, Any],
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the orchestrator.

        Args:
            config: Configuration dictionary with system settings
            logger: Optional logger (creates one if not provided)
        """
        self.config = config
        self.logger = logger or logging.getLogger('orchestrator')

        # Services registry
        self.services: Dict[str, EventDrivenService] = {}
        self.service_order: List[str] = []

        # Infrastructure components
        self.event_bus: Optional[EventBus] = None

        # State
        self.status = OrchestratorStatus.INITIALIZING
        self.start_time: Optional[datetime] = None
        self.last_health_check: Optional[datetime] = None

        # Configuration
        self.enable_auto_restart = config.get('enable_auto_restart', False)
        self.health_check_interval = config.get('health_check_interval', 60)
        self.symbol = config.get('symbol', 'UNKNOWN')

        self.logger.info(f"TradingOrchestrator created for {self.symbol}")

    @classmethod
    def from_config(
        cls,
        config: SystemConfig,
        client: Any,
        data_source: Any,
        indicator_processor: Any,
        regime_manager: Any,
        strategy_engine: Any,
        entry_manager: Any,
        trade_executor: Any,
        date_helper: Any,
        logger: Optional[logging.Logger] = None
    ) -> "TradingOrchestrator":
        """
        Create TradingOrchestrator from SystemConfig.

        This factory method creates and fully initializes an orchestrator
        from a SystemConfig object.

        Args:
            config: SystemConfig with all configuration
            client: MT5 Client
            data_source: DataSourceManager
            indicator_processor: IndicatorProcessor
            regime_manager: RegimeManager
            strategy_engine: StrategyEngine
            entry_manager: EntryManager
            trade_executor: TradeExecutor
            date_helper: DateHelper
            logger: Optional logger

        Returns:
            Fully initialized TradingOrchestrator

        Example:
            ```python
            # Load configuration
            config = ConfigLoader.load("config/services.yaml")

            # Create orchestrator from config
            orchestrator = TradingOrchestrator.from_config(
                config=config,
                client=mt5_client,
                data_source=data_source,
                indicator_processor=indicator_processor,
                regime_manager=regime_manager,
                strategy_engine=strategy_engine,
                entry_manager=entry_manager,
                trade_executor=trade_executor,
                date_helper=date_helper,
                logger=logger
            )

            # Start and run
            orchestrator.start()
            orchestrator.run(interval_seconds=config.services.data_fetching.fetch_interval)
            ```
        """
        # Convert SystemConfig to orchestrator config dict
        orchestrator_config = config.to_orchestrator_config()

        # Create orchestrator
        orchestrator = cls(config=orchestrator_config, logger=logger)

        # Initialize with all components
        orchestrator.initialize(
            client=client,
            data_source=data_source,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            trade_executor=trade_executor,
            date_helper=date_helper
        )

        return orchestrator

    @classmethod
    def from_config_file(
        cls,
        config_path: str,
        client: Any,
        data_source: Any,
        indicator_processor: Any,
        regime_manager: Any,
        strategy_engine: Any,
        entry_manager: Any,
        trade_executor: Any,
        date_helper: Any,
        logger: Optional[logging.Logger] = None
    ) -> "TradingOrchestrator":
        """
        Create TradingOrchestrator from configuration file.

        Convenience method that loads config from file and creates orchestrator.

        Args:
            config_path: Path to YAML configuration file
            client: MT5 Client
            data_source: DataSourceManager
            indicator_processor: IndicatorProcessor
            regime_manager: RegimeManager
            strategy_engine: StrategyEngine
            entry_manager: EntryManager
            trade_executor: TradeExecutor
            date_helper: DateHelper
            logger: Optional logger

        Returns:
            Fully initialized TradingOrchestrator

        Example:
            ```python
            orchestrator = TradingOrchestrator.from_config_file(
                config_path="config/services.yaml",
                client=mt5_client,
                data_source=data_source,
                indicator_processor=indicator_processor,
                regime_manager=regime_manager,
                strategy_engine=strategy_engine,
                entry_manager=entry_manager,
                trade_executor=trade_executor,
                date_helper=date_helper
            )
            ```
        """
        # Load configuration
        config = ConfigLoader.load(config_path=config_path, logger=logger)

        # Create from config
        return cls.from_config(
            config=config,
            client=client,
            data_source=data_source,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            trade_executor=trade_executor,
            date_helper=date_helper,
            logger=logger
        )

    def initialize(
        self,
        client: Any,
        data_source: Any,
        indicator_processor: Any,
        regime_manager: Any,
        strategy_engine: Any,
        entry_manager: Any,
        trade_executor: Any,
        date_helper: Any
    ):
        """
        Initialize all services with their dependencies.

        This method creates all services and registers them in the correct order.

        Args:
            client: MT5 Client
            data_source: DataSourceManager
            indicator_processor: IndicatorProcessor
            regime_manager: RegimeManager
            strategy_engine: StrategyEngine
            entry_manager: EntryManager
            trade_executor: TradeExecutor
            date_helper: DateHelper
        """
        self.logger.info("=== INITIALIZING TRADING SYSTEM ===")

        # Step 1: Create EventBus
        self.logger.info("Creating EventBus...")
        self.event_bus = EventBus(
            event_history_limit=self.config.get('event_history_limit', 1000),
            log_all_events=self.config.get('log_all_events', False)
        )

        # Step 2: Create services in dependency order
        self._create_data_service(data_source)
        self._create_indicator_service(indicator_processor, regime_manager)
        self._create_strategy_service(strategy_engine, entry_manager)
        self._create_execution_service(trade_executor, date_helper)

        self.logger.info(f"=== INITIALIZED {len(self.services)} SERVICES ===")

    def _create_data_service(self, data_source: Any):
        """Create DataFetchingService."""
        from app.services.data_fetching import DataFetchingService

        self.logger.info("Creating DataFetchingService...")

        service = DataFetchingService(
            event_bus=self.event_bus,
            data_source=data_source,
            config={
                "symbol": self.config['symbol'],
                "timeframes": self.config['timeframes'],
                "candle_index": self.config.get('candle_index', 1),
                "nbr_bars": self.config.get('nbr_bars', 3)
            }
        )

        self.services['data_fetching'] = service
        self.service_order.append('data_fetching')
        self.logger.info("✓ DataFetchingService created")

    def _create_indicator_service(
        self,
        indicator_processor: Any,
        regime_manager: Any
    ):
        """Create IndicatorCalculationService."""
        from app.services.indicator_calculation import IndicatorCalculationService

        self.logger.info("Creating IndicatorCalculationService...")

        service = IndicatorCalculationService(
            event_bus=self.event_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config={
                "symbol": self.config['symbol'],
                "timeframes": self.config['timeframes'],
                "track_regime_changes": self.config.get('track_regime_changes', True)
            }
        )

        self.services['indicator_calculation'] = service
        self.service_order.append('indicator_calculation')
        self.logger.info("✓ IndicatorCalculationService created")

    def _create_strategy_service(
        self,
        strategy_engine: Any,
        entry_manager: Any
    ):
        """Create StrategyEvaluationService."""
        from app.services.strategy_evaluation import StrategyEvaluationService

        self.logger.info("Creating StrategyEvaluationService...")

        service = StrategyEvaluationService(
            event_bus=self.event_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config={
                "symbol": self.config['symbol'],
                "min_rows_required": self.config.get('min_rows_required', 3)
            }
        )

        self.services['strategy_evaluation'] = service
        self.service_order.append('strategy_evaluation')
        self.logger.info("✓ StrategyEvaluationService created")

    def _create_execution_service(
        self,
        trade_executor: Any,
        date_helper: Any
    ):
        """Create TradeExecutionService."""
        from app.services.trade_execution import TradeExecutionService

        self.logger.info("Creating TradeExecutionService...")

        service = TradeExecutionService(
            event_bus=self.event_bus,
            trade_executor=trade_executor,
            date_helper=date_helper,
            config={
                "symbol": self.config['symbol'],
                "execution_mode": self.config.get('execution_mode', 'immediate')
            }
        )

        self.services['trade_execution'] = service
        self.service_order.append('trade_execution')
        self.logger.info("✓ TradeExecutionService created")

    def start(self):
        """Start all services in dependency order."""
        self.logger.info("=== STARTING ALL SERVICES ===")

        for service_name in self.service_order:
            try:
                service = self.services[service_name]
                service.start()
                self.logger.info(f"✓ {service_name} started")
            except Exception as e:
                self.logger.error(f"Failed to start {service_name}: {e}", exc_info=True)
                self.status = OrchestratorStatus.ERROR
                raise

        self.status = OrchestratorStatus.RUNNING
        self.start_time = datetime.now()
        self.logger.info("=== ALL SERVICES STARTED ===")

    def stop(self):
        """Stop all services gracefully in reverse order."""
        self.logger.info("=== STOPPING ALL SERVICES ===")
        self.status = OrchestratorStatus.STOPPING

        # Stop in reverse order
        for service_name in reversed(self.service_order):
            try:
                service = self.services[service_name]
                service.stop()
                self.logger.info(f"✓ {service_name} stopped")
            except Exception as e:
                self.logger.error(f"Error stopping {service_name}: {e}", exc_info=True)

        self.status = OrchestratorStatus.STOPPED
        self.logger.info("=== ALL SERVICES STOPPED ===")

    def run(self, interval_seconds: int = 5, max_iterations: Optional[int] = None):
        """
        Run the trading loop.

        Args:
            interval_seconds: Seconds between each cycle
            max_iterations: Maximum iterations (None for infinite)
        """
        self.logger.info(f"=== STARTING TRADING LOOP (interval={interval_seconds}s) ===")

        iteration = 0

        try:
            while True:
                # Check max iterations
                if max_iterations and iteration >= max_iterations:
                    self.logger.info(f"Reached max iterations: {max_iterations}")
                    break

                iteration += 1

                # Fetch data (triggers entire event chain)
                data_service = self.services['data_fetching']
                success_count = data_service.fetch_streaming_data()

                # Log status every 10 iterations
                if iteration % 10 == 0:
                    self._log_status(iteration)

                # Health check every N iterations
                check_interval_iterations = self.health_check_interval // interval_seconds
                if iteration % max(check_interval_iterations, 1) == 0:
                    self._perform_health_check()

                # Sleep
                time.sleep(interval_seconds)

        except KeyboardInterrupt:
            self.logger.info("Received keyboard interrupt")
        except Exception as e:
            self.logger.error(f"Fatal error in trading loop: {e}", exc_info=True)
            self.status = OrchestratorStatus.ERROR
        finally:
            self.stop()

    def _perform_health_check(self):
        """Perform health check on all services."""
        self.last_health_check = datetime.now()

        health_status = self.get_service_health()
        unhealthy = [name for name, healthy in health_status.items() if not healthy]

        if unhealthy:
            self.logger.warning(f"Unhealthy services: {unhealthy}")

            if self.enable_auto_restart:
                for service_name in unhealthy:
                    self.logger.info(f"Attempting to restart {service_name}...")
                    try:
                        self.restart_service(service_name)
                    except Exception as e:
                        self.logger.error(f"Failed to restart {service_name}: {e}")
        else:
            self.logger.debug("All services healthy")

    def restart_service(self, service_name: str):
        """
        Restart a specific service.

        Args:
            service_name: Name of the service to restart
        """
        if service_name not in self.services:
            raise ValueError(f"Unknown service: {service_name}")

        self.logger.info(f"Restarting service: {service_name}")

        service = self.services[service_name]

        # Stop service
        try:
            service.stop()
        except Exception as e:
            self.logger.error(f"Error stopping {service_name}: {e}")

        # Wait a bit
        time.sleep(1)

        # Start service
        service.start()
        self.logger.info(f"✓ {service_name} restarted")

    def get_service_health(self) -> Dict[str, bool]:
        """
        Get health status of all services.

        Returns:
            Dictionary mapping service name to health status
        """
        return {
            name: service.health_check().is_healthy
            for name, service in self.services.items()
        }

    def get_service_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get metrics from all services.

        Returns:
            Dictionary mapping service name to metrics
        """
        return {
            name: service.get_metrics()
            for name, service in self.services.items()
        }

    def get_orchestrator_metrics(self) -> Dict[str, Any]:
        """
        Get orchestrator-level metrics.

        Returns:
            Dictionary with orchestrator metrics
        """
        uptime = 0.0
        if self.start_time:
            uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            "status": self.status.value,
            "uptime_seconds": uptime,
            "services_count": len(self.services),
            "services_healthy": sum(self.get_service_health().values()),
            "last_health_check": self.last_health_check.isoformat() if self.last_health_check else None,
        }

    def _log_status(self, iteration: int):
        """Log system status."""
        metrics = self.get_service_metrics()

        self.logger.info(f"=== STATUS (iteration {iteration}) ===")
        self.logger.info(f"Data Fetches: {metrics['data_fetching'].get('data_fetches', 0)}")
        self.logger.info(f"New Candles: {metrics['data_fetching'].get('new_candles_detected', 0)}")
        self.logger.info(f"Indicators Calculated: {metrics['indicator_calculation'].get('indicators_calculated', 0)}")
        self.logger.info(f"Regime Changes: {metrics['indicator_calculation'].get('regime_changes_detected', 0)}")
        self.logger.info(f"Strategies Evaluated: {metrics['strategy_evaluation'].get('strategies_evaluated', 0)}")
        self.logger.info(f"Entry Signals: {metrics['strategy_evaluation'].get('entry_signals_generated', 0)}")
        self.logger.info(f"Exit Signals: {metrics['strategy_evaluation'].get('exit_signals_generated', 0)}")
        self.logger.info(f"Trades Executed: {metrics['trade_execution'].get('trades_executed', 0)}")

    def get_event_bus_metrics(self) -> Dict[str, Any]:
        """
        Get metrics from the EventBus.

        Returns:
            Dictionary with EventBus metrics
        """
        if self.event_bus:
            return self.event_bus.get_metrics()
        return {}

    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all system metrics.

        Returns:
            Dictionary with all metrics
        """
        return {
            "orchestrator": self.get_orchestrator_metrics(),
            "services": self.get_service_metrics(),
            "event_bus": self.get_event_bus_metrics(),
        }

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"TradingOrchestrator("
            f"symbol={self.symbol}, "
            f"status={self.status.value}, "
            f"services={len(self.services)}"
            f")"
        )
