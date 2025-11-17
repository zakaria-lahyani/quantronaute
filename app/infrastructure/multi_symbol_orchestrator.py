"""
Multi-Symbol Trading Orchestrator.

This orchestrator manages trading services for multiple symbols simultaneously.
Each symbol gets its own set of services (DataFetching, Indicator, Strategy, Execution)
for complete isolation and independent operation.

Key improvements over single-symbol orchestrator:
- Supports trading multiple symbols concurrently
- Each symbol has isolated services for better error handling
- Per-symbol health monitoring and metrics
- Per-symbol component management (indicators, strategies, executors)
"""

import logging
import time
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from app.infrastructure.event_bus import EventBus
from app.services.base import EventDrivenService, ServiceStatus, HealthStatus
from app.infrastructure.config import SystemConfig, ConfigLoader
from app.risk.account_stop_loss import AccountStopLossManager, AccountStopLossConfig, StopLossStatus


class OrchestratorStatus(Enum):
    """Orchestrator status enumeration."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class MultiSymbolTradingOrchestrator:
    """
    Orchestrates trading system for multiple symbols.

    Architecture:
        - One EventBus (shared across all symbols for correlation)
        - Per symbol: 4 services (DataFetching, Indicator, Strategy, Execution)
        - Per symbol: Components (IndicatorProcessor, StrategyEngine, EntryManager, TradeExecutor)

    Example:
        ```python
        # Create orchestrator for multiple symbols
        orchestrator = MultiSymbolTradingOrchestrator(config={
            "symbols": ["XAUUSD", "BTCUSD", "EURUSD"],
            "timeframes": ["1", "5", "15"],
            "enable_auto_restart": True
        })

        # Initialize with per-symbol components
        orchestrator.initialize(
            client=mt5_client,
            data_source=data_source,
            symbol_components={
                "XAUUSD": {
                    "indicator_processor": xau_processor,
                    "regime_manager": xau_regime,
                    "strategy_engine": xau_engine,
                    "entry_manager": xau_entry,
                    "trade_executor": xau_executor
                },
                "BTCUSD": { ... },
                "EURUSD": { ... }
            },
            date_helper=date_helper
        )

        # Start trading
        orchestrator.start()
        orchestrator.run(interval_seconds=5)
        ```
    """

    def __init__(
        self,
        config: Dict[str, Any],
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the multi-symbol orchestrator.

        Args:
            config: Configuration dictionary with:
                - symbols: List[str] - Symbols to trade
                - timeframes: List[str] - Timeframes to monitor
                - enable_auto_restart: bool - Auto-restart services on failure
                - health_check_interval: int - Health check interval in seconds
            logger: Optional logger
        """
        self.config = config
        self.logger = logger or logging.getLogger('multi-symbol-orchestrator')

        # Symbol configuration
        self.symbols = config.get('symbols', [])
        if not self.symbols:
            raise ValueError("At least one symbol must be specified in config['symbols']")

        self.timeframes = config.get('timeframes', [])

        # Services registry (symbol -> service_name -> service)
        self.services: Dict[str, Dict[str, EventDrivenService]] = {
            symbol: {} for symbol in self.symbols
        }

        # Service order per symbol
        self.service_order = ["data_fetching", "indicator_calculation", "strategy_evaluation", "trade_execution", "position_monitor"]

        # Infrastructure components (shared)
        self.event_bus: Optional[EventBus] = None
        self.account_stop_loss: Optional[AccountStopLossManager] = None
        self.automation_state_manager: Optional[Any] = None  # AutomationStateManager
        self.automation_file_watcher: Optional[Any] = None  # AutomationFileWatcher

        # State
        self.status = OrchestratorStatus.INITIALIZING
        self.start_time: Optional[datetime] = None
        self.last_health_check: Optional[datetime] = None
        self.last_account_check: Optional[datetime] = None

        # Configuration
        self.enable_auto_restart = config.get('enable_auto_restart', False)
        self.health_check_interval = config.get('health_check_interval', 60)
        self.account_check_interval = config.get('account_check_interval', 10)  # Check account every 10s

        self.logger.info(f"MultiSymbolTradingOrchestrator created for symbols: {self.symbols}")

    @classmethod
    def from_config(
        cls,
        config: SystemConfig,
        client: Any,
        data_source: Any,
        symbol_components: Dict[str, Dict[str, Any]],
        date_helper: Any,
        logger: Optional[logging.Logger] = None
    ) -> "MultiSymbolTradingOrchestrator":
        """
        Create orchestrator from SystemConfig with per-symbol components.

        Args:
            config: SystemConfig with all configuration
            client: MT5 Client (shared)
            data_source: DataSourceManager (shared)
            symbol_components: Dict mapping symbol -> components dict with:
                - indicator_processor: IndicatorProcessor
                - regime_manager: RegimeManager
                - strategy_engine: StrategyEngine
                - entry_manager: EntryManager
                - trade_executor: TradeExecutor
            date_helper: DateHelper (shared)
            logger: Optional logger

        Returns:
            Fully initialized MultiSymbolTradingOrchestrator

        Example:
            ```python
            config = ConfigLoader.load("config/services.yaml")

            orchestrator = MultiSymbolTradingOrchestrator.from_config(
                config=config,
                client=mt5_client,
                data_source=data_source,
                symbol_components={
                    "XAUUSD": {
                        "indicator_processor": xau_processor,
                        "regime_manager": xau_regime,
                        "strategy_engine": xau_engine,
                        "entry_manager": xau_entry,
                        "trade_executor": xau_executor
                    },
                    "BTCUSD": { ... }
                },
                date_helper=date_helper,
                logger=logger
            )
            ```
        """
        # Convert SystemConfig to orchestrator config dict
        orchestrator_config = config.to_orchestrator_config()

        # Create orchestrator
        orchestrator = cls(config=orchestrator_config, logger=logger)

        # Initialize with components
        orchestrator.initialize(
            client=client,
            data_source=data_source,
            symbol_components=symbol_components,
            date_helper=date_helper
        )

        return orchestrator

    def initialize(
        self,
        client: Any,
        data_source: Any,
        symbol_components: Dict[str, Dict[str, Any]],
        date_helper: Any,
        account_stop_loss_config: Optional[AccountStopLossConfig] = None
    ):
        """
        Initialize all services for all symbols.

        Args:
            client: MT5 Client (shared)
            data_source: DataSourceManager (shared)
            symbol_components: Dict mapping symbol -> components
            date_helper: DateHelper (shared)
            account_stop_loss_config: Optional account-level stop loss configuration
        """
        self.logger.info("=== INITIALIZING MULTI-SYMBOL TRADING SYSTEM ===")
        self.logger.info(f"Symbols: {self.symbols}")
        self.logger.info(f"Timeframes: {self.timeframes}")

        # Step 1: Create shared EventBus
        self.logger.info("Creating shared EventBus...")
        self.event_bus = EventBus(
            event_history_limit=self.config.get('event_history_limit', 1000),
            log_all_events=self.config.get('log_all_events', False)
        )

        # Step 1.5: Create automation control components
        self.logger.info("Creating automation control components...")
        try:
            from app.infrastructure.automation_state_manager import AutomationStateManager
            from app.infrastructure.automation_file_watcher import AutomationFileWatcher

            # Get automation config (with defaults)
            automation_config = self.config.get('automation', {})
            automation_enabled = automation_config.get('enabled', True)
            state_file = automation_config.get('state_file', 'config/automation_state.json')
            toggle_file = automation_config.get('toggle_file', 'config/toggle_automation.txt')
            file_watcher_enabled = automation_config.get('file_watcher_enabled', True)
            file_watcher_interval = automation_config.get('file_watcher_interval', 5)

            # Create AutomationStateManager
            self.automation_state_manager = AutomationStateManager(
                event_bus=self.event_bus,
                state_file_path=state_file,
                default_enabled=automation_enabled,
                logger=logging.getLogger('automation-state')
            )
            self.logger.info(f"  ✓ AutomationStateManager created (default_enabled={automation_enabled})")

            # Create AutomationFileWatcher (if enabled)
            if file_watcher_enabled:
                self.automation_file_watcher = AutomationFileWatcher(
                    event_bus=self.event_bus,
                    toggle_file_path=toggle_file,
                    poll_interval=file_watcher_interval,
                    logger=logging.getLogger('automation-watcher')
                )
                self.logger.info(f"  ✓ AutomationFileWatcher created (poll_interval={file_watcher_interval}s)")
            else:
                self.logger.info("  ⊘ AutomationFileWatcher disabled via config")

        except Exception as e:
            self.logger.error(f"  ✗ Failed to initialize automation components: {e}", exc_info=True)
            self.automation_state_manager = None
            self.automation_file_watcher = None

        # Step 1.6: Create account-level stop loss manager
        if account_stop_loss_config:
            self.logger.info("Creating account-level stop loss manager...")
            self.account_stop_loss = AccountStopLossManager(
                config=account_stop_loss_config,
                client=client,
                logger=logging.getLogger('account-stop-loss')
            )

            # Initialize with current balance
            try:
                current_balance = client.account.get_balance()
                self.account_stop_loss.initialize(current_balance)
                self.logger.info(f"  ✓ Account stop loss initialized with balance: ${current_balance:,.2f}")
            except Exception as e:
                self.logger.error(f"  ✗ Failed to initialize account stop loss: {e}")
        else:
            self.logger.info("Account-level stop loss not configured (skipping)")

        # Step 1.7: Inject event_bus into all trade executors' order executors
        self.logger.info("Configuring event bus for order executors...")
        for symbol, components in symbol_components.items():
            trade_executor = components.get('trade_executor')
            if trade_executor and hasattr(trade_executor, 'order_executor'):
                order_executor = trade_executor.order_executor
                if hasattr(order_executor, 'set_event_bus'):
                    order_executor.set_event_bus(self.event_bus)
                    self.logger.info(f"  ✓ Event bus configured for {symbol} OrderExecutor")

        # Step 2: Create services for each symbol
        for symbol in self.symbols:
            self.logger.info(f"\n--- Initializing services for {symbol} ---")

            if symbol not in symbol_components:
                raise ValueError(f"No components provided for symbol {symbol}")

            components = symbol_components[symbol]

            # Get symbol-specific timeframes from components
            symbol_timeframes = components.get('timeframes', self.timeframes)

            # Create services for this symbol
            self._create_services_for_symbol(
                symbol=symbol,
                client=client,
                data_source=data_source,
                indicator_processor=components['indicator_processor'],
                regime_manager=components['regime_manager'],
                strategy_engine=components['strategy_engine'],
                entry_manager=components['entry_manager'],
                trade_executor=components['trade_executor'],
                date_helper=date_helper,
                symbol_timeframes=symbol_timeframes
            )

        total_services = sum(len(services) for services in self.services.values())
        self.logger.info(f"\n=== INITIALIZED {total_services} SERVICES ({len(self.symbols)} symbols x 5 services) ===")

    def _create_services_for_symbol(
        self,
        symbol: str,
        client: Any,
        data_source: Any,
        indicator_processor: Any,
        regime_manager: Any,
        strategy_engine: Any,
        entry_manager: Any,
        trade_executor: Any,
        date_helper: Any,
        symbol_timeframes: List[str]
    ):
        """Create all services for a specific symbol."""
        # Import services here to avoid circular imports
        from app.services.data_fetching import DataFetchingService
        from app.services.indicator_calculation import IndicatorCalculationService
        from app.services.strategy_evaluation import StrategyEvaluationService
        from app.services.trade_execution import TradeExecutionService
        from app.services.position_monitor import PositionMonitorService

        # 1. DataFetchingService
        self.logger.info(f"  Creating DataFetchingService for {symbol}...")
        self.logger.info(f"    Using symbol-specific timeframes: {symbol_timeframes}")
        data_config = {
            "symbol": symbol,
            "timeframes": symbol_timeframes,  # Use symbol-specific timeframes
            "candle_index": self.config.get('candle_index', 1),
            "nbr_bars": self.config.get('nbr_bars', 3)
        }
        data_service = DataFetchingService(
            event_bus=self.event_bus,
            data_source=data_source,
            config=data_config,
            logger=logging.getLogger(f'data-fetching-{symbol.lower()}')
        )
        self.services[symbol]['data_fetching'] = data_service

        # 2. IndicatorCalculationService
        self.logger.info(f"  Creating IndicatorCalculationService for {symbol}...")
        indicator_config = {
            "symbol": symbol,
            "timeframes": symbol_timeframes,  # Use symbol-specific timeframes
            "track_regime_changes": self.config.get('track_regime_changes', True)
        }
        indicator_service = IndicatorCalculationService(
            event_bus=self.event_bus,
            indicator_processor=indicator_processor,
            regime_manager=regime_manager,
            config=indicator_config,
            logger=logging.getLogger(f'indicator-calc-{symbol.lower()}')
        )
        self.services[symbol]['indicator_calculation'] = indicator_service

        # 3. StrategyEvaluationService
        self.logger.info(f"  Creating StrategyEvaluationService for {symbol}...")
        strategy_config = {
            "symbol": symbol,
            "min_rows_required": self.config.get('min_rows_required', 3)
        }
        strategy_service = StrategyEvaluationService(
            event_bus=self.event_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            client=client,  # Pass client for account balance fetching
            config=strategy_config,
            logger=logging.getLogger(f'strategy-eval-{symbol.lower()}')
        )
        self.services[symbol]['strategy_evaluation'] = strategy_service

        # 4. TradeExecutionService
        self.logger.info(f"  Creating TradeExecutionService for {symbol}...")
        execution_config = {
            "symbol": symbol,
            "execution_mode": self.config.get('execution_mode', 'immediate'),
            "batch_size": self.config.get('batch_size', 1)
        }
        execution_service = TradeExecutionService(
            event_bus=self.event_bus,
            trade_executor=trade_executor,
            date_helper=date_helper,
            config=execution_config,
            logger=logging.getLogger(f'trade-exec-{symbol.lower()}')
        )
        self.services[symbol]['trade_execution'] = execution_service

        # 5. PositionMonitorService
        self.logger.info(f"  Creating PositionMonitorService for {symbol}...")
        position_monitor_config = {
            "symbol": symbol,
            "check_interval": self.config.get('position_check_interval', 1),  # Check every second
            "enable_tp_management": self.config.get('enable_tp_management', True),
            "enable_sl_management": self.config.get('enable_sl_management', True)
        }
        position_monitor_service = PositionMonitorService(
            event_bus=self.event_bus,
            client=client,
            config=position_monitor_config,
            logger=logging.getLogger(f'position-monitor-{symbol.lower()}')
        )
        self.services[symbol]['position_monitor'] = position_monitor_service

        self.logger.info(f"  ✓ All services created for {symbol}")

    def start(self):
        """Start all services for all symbols and automation components."""
        self.logger.info("\n=== STARTING ALL SERVICES ===")
        self.status = OrchestratorStatus.RUNNING
        self.start_time = datetime.now()

        # Start automation file watcher (if enabled)
        if self.automation_file_watcher:
            try:
                self.automation_file_watcher.start()
                self.logger.info("  ✓ AutomationFileWatcher started")
            except Exception as e:
                self.logger.error(f"  ✗ Failed to start AutomationFileWatcher: {e}", exc_info=True)

        for symbol in self.symbols:
            self.logger.info(f"\n--- Starting services for {symbol} ---")
            for service_name in self.service_order:
                service = self.services[symbol][service_name]
                try:
                    service.start()
                    self.logger.info(f"  ✓ {service_name} started")
                except Exception as e:
                    self.logger.error(f"  ✗ Failed to start {service_name}: {e}", exc_info=True)
                    raise

        self.logger.info("\n=== ALL SERVICES STARTED SUCCESSFULLY ===")

    def stop(self):
        """Stop all services and automation components gracefully."""
        self.logger.info("\n=== STOPPING ALL SERVICES ===")
        self.status = OrchestratorStatus.STOPPING

        # Stop in reverse order
        for symbol in reversed(self.symbols):
            self.logger.info(f"\n--- Stopping services for {symbol} ---")
            for service_name in reversed(self.service_order):
                service = self.services[symbol].get(service_name)
                if service:
                    try:
                        service.stop()
                        self.logger.info(f"  ✓ {service_name} stopped")
                    except Exception as e:
                        self.logger.error(f"  ✗ Error stopping {service_name}: {e}")

        # Stop automation file watcher
        if self.automation_file_watcher:
            try:
                self.automation_file_watcher.stop()
                self.logger.info("  ✓ AutomationFileWatcher stopped")
            except Exception as e:
                self.logger.error(f"  ✗ Error stopping AutomationFileWatcher: {e}")

        self.status = OrchestratorStatus.STOPPED
        self.logger.info("\n=== ALL SERVICES STOPPED ===")

    def run(self, interval_seconds: int = 5):
        """
        Run the trading loop.

        Args:
            interval_seconds: Data fetch interval
        """
        self.logger.info(f"\n=== STARTING TRADING LOOP (interval: {interval_seconds}s) ===")

        iteration = 0
        status_log_interval = self.config.get('status_log_interval', 10)

        try:
            while self.status == OrchestratorStatus.RUNNING:
                iteration += 1
                iteration_start = time.time()

                # Log status periodically
                if iteration % status_log_interval == 0:
                    self.logger.info(f"\n--- Iteration {iteration} ---")

                # Check account-level stop loss FIRST
                if self.account_stop_loss and self._should_perform_account_check():
                    if not self._perform_account_check():
                        # Account stop loss triggered - stop trading
                        self.logger.error("Account stop loss triggered - stopping all trading")
                        break

                # Fetch data for all symbols (only if trading allowed)
                if not self.account_stop_loss or self.account_stop_loss.is_trading_allowed():
                    for symbol in self.symbols:
                        # Fetch data
                        data_service = self.services[symbol]['data_fetching']
                        try:
                            data_service.fetch_streaming_data()
                        except Exception as e:
                            self.logger.error(f"Error fetching data for {symbol}: {e}", exc_info=True)

                        # Check positions for TP management
                        position_monitor = self.services[symbol].get('position_monitor')
                        if position_monitor and position_monitor._status == ServiceStatus.RUNNING:
                            try:
                                position_monitor.check_positions()
                            except Exception as e:
                                self.logger.error(f"Error checking positions for {symbol}: {e}", exc_info=True)
                else:
                    self.logger.warning("Trading stopped by account stop loss - skipping data fetch")

                # Health check
                if self._should_perform_health_check():
                    self._perform_health_check()

                # Sleep to maintain interval
                elapsed = time.time() - iteration_start
                sleep_time = max(0, interval_seconds - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except KeyboardInterrupt:
            self.logger.info("\nReceived interrupt signal, stopping gracefully...")
            self.stop()

    def _should_perform_health_check(self) -> bool:
        """Check if it's time for health check."""
        if self.last_health_check is None:
            return True

        elapsed = (datetime.now() - self.last_health_check).total_seconds()
        return elapsed >= self.health_check_interval

    def _should_perform_account_check(self) -> bool:
        """Check if it's time for account stop loss check."""
        if self.last_account_check is None:
            return True

        elapsed = (datetime.now() - self.last_account_check).total_seconds()
        return elapsed >= self.account_check_interval

    def _perform_account_check(self) -> bool:
        """
        Perform account-level stop loss check.

        Returns:
            True if trading allowed, False if stopped
        """
        if not self.account_stop_loss:
            return True

        self.last_account_check = datetime.now()

        try:
            # Get current account balance
            from app.clients.mt5.client import MT5Client
            # Assuming we have access to client through services
            # In practice, you'd pass client to initialize()
            # For now, we'll skip actual balance fetch and assume it's updated elsewhere

            # Update metrics (would be called with actual balance)
            # self.account_stop_loss.update_account_metrics(
            #     current_balance=current_balance,
            #     open_positions_count=total_positions,
            #     total_exposure=total_exposure
            # )

            # Check if trading is allowed
            if not self.account_stop_loss.is_trading_allowed():
                reason = self.account_stop_loss.get_stop_reason()
                self.logger.error(f" ACCOUNT STOP LOSS: {reason}")

                # Stop all trading services
                if self.account_stop_loss.config.stop_trading_on_breach:
                    self.logger.warning("Stopping all trading services...")
                    self._stop_all_trading_services()

                return False

            return True

        except Exception as e:
            self.logger.error(f"Error performing account check: {e}", exc_info=True)
            return True  # Allow trading on error (fail-open)

    def _stop_all_trading_services(self):
        """Stop all trading-related services (keep monitoring services)."""
        for symbol in self.symbols:
            # Stop trade execution services
            execution_service = self.services[symbol].get('trade_execution')
            if execution_service:
                try:
                    execution_service.stop()
                    self.logger.info(f"  ✓ Stopped trade execution for {symbol}")
                except Exception as e:
                    self.logger.error(f"  ✗ Error stopping {symbol} execution: {e}")

            # Optionally stop strategy evaluation
            strategy_service = self.services[symbol].get('strategy_evaluation')
            if strategy_service:
                try:
                    strategy_service.stop()
                    self.logger.info(f"  ✓ Stopped strategy evaluation for {symbol}")
                except Exception as e:
                    self.logger.error(f"  ✗ Error stopping {symbol} strategy: {e}")

    def _perform_health_check(self):
        """Perform health check on all services."""
        self.last_health_check = datetime.now()

        unhealthy_services = []

        for symbol in self.symbols:
            for service_name in self.service_order:
                service = self.services[symbol][service_name]
                health = service.health_check()

                if not health.is_healthy:
                    unhealthy_services.append((symbol, service_name, health))

        if unhealthy_services:
            self.logger.warning(f"  Found {len(unhealthy_services)} unhealthy services:")
            for symbol, service_name, health in unhealthy_services:
                self.logger.warning(f"  - {symbol}/{service_name}: {health.status.value}")

            if self.enable_auto_restart:
                self._restart_unhealthy_services(unhealthy_services)

    def _restart_unhealthy_services(self, unhealthy_services: List):
        """Restart unhealthy services."""
        for symbol, service_name, health in unhealthy_services:
            self.logger.info(f" Restarting {symbol}/{service_name}...")
            try:
                service = self.services[symbol][service_name]
                service.stop()
                time.sleep(1)
                service.start()
                self.logger.info(f"✓ {symbol}/{service_name} restarted successfully")
            except Exception as e:
                self.logger.error(f"✗ Failed to restart {symbol}/{service_name}: {e}")

    def get_service_health(self) -> Dict[str, Dict[str, bool]]:
        """Get health status for all services."""
        health_status = {}

        for symbol in self.symbols:
            health_status[symbol] = {}
            for service_name in self.service_order:
                service = self.services[symbol][service_name]
                health = service.health_check()
                health_status[symbol][service_name] = health.is_healthy

        return health_status

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics for all services and symbols."""
        metrics = {
            "orchestrator": {
                "status": self.status.value,
                "symbols": self.symbols,
                "uptime_seconds": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                "total_services": sum(len(services) for services in self.services.values()),
                "symbols_count": len(self.symbols),
            },
            "automation": self.automation_state_manager.get_state() if self.automation_state_manager else None,
            "account_stop_loss": self.account_stop_loss.get_metrics_summary() if self.account_stop_loss else None,
            "services": {},
            "event_bus": self.event_bus.get_metrics() if self.event_bus else {}
        }

        # Per-symbol service metrics
        for symbol in self.symbols:
            metrics["services"][symbol] = {}
            for service_name in self.service_order:
                service = self.services[symbol][service_name]
                metrics["services"][symbol][service_name] = service.get_metrics()

        return metrics

    def get_uptime_seconds(self) -> float:
        """Get orchestrator uptime in seconds."""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0
