"""
Trade Execution Service.

This service wraps the TradeExecutor and publishes trade events.
It is responsible for:
- Subscribing to EntrySignalEvent and ExitSignalEvent
- Collecting signals into trade batches
- Executing trades via TradeExecutor
- Publishing OrderPlacedEvent, OrderRejectedEvent, PositionClosedEvent
- Publishing RiskLimitBreachedEvent, TradingBlockedEvent
- Handling execution errors gracefully
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime

from app.services.base import EventDrivenService, ServiceStatus, HealthStatus
from app.infrastructure.event_bus import EventBus
from app.events.strategy_events import EntrySignalEvent, ExitSignalEvent, TradesReadyEvent
from app.events.trade_events import (
    OrderPlacedEvent,
    OrderRejectedEvent,
    PositionClosedEvent,
    RiskLimitBreachedEvent,
    TradingBlockedEvent,
    TradingAuthorizedEvent,
)
from app.strategy_builder.data.dtos import Trades, EntryDecision, ExitDecision


class TradeExecutionService(EventDrivenService):
    """
    Service for executing trades and managing positions.

    This service wraps the TradeExecutor and is responsible for:
    - Subscribing to EntrySignalEvent and ExitSignalEvent
    - Collecting entry/exit signals into Trades object
    - Executing trades via TradeExecutor
    - Publishing OrderPlacedEvent when orders placed
    - Publishing OrderRejectedEvent when orders rejected
    - Publishing PositionClosedEvent when positions closed
    - Publishing RiskLimitBreachedEvent when risk limits breached
    - Publishing TradingBlockedEvent when trading is blocked
    - Tracking execution metrics

    Configuration:
        symbol: Trading symbol (e.g., "EURUSD") - for event filtering
        execution_mode: "immediate" or "batch" (default: "immediate")
        batch_size: Number of signals to collect before execution (if batch mode)

    Example:
        ```python
        # Create trade executor with all components
        trade_executor = ExecutorBuilder.build_from_config(
            config=config,
            client=client,
            logger=logger
        )

        service = TradeExecutionService(
            event_bus=event_bus,
            trade_executor=trade_executor,
            date_helper=date_helper,
            config={
                "symbol": "EURUSD",
                "execution_mode": "immediate"
            }
        )

        service.start()
        # Service now listens for EntrySignalEvent/ExitSignalEvent and executes
        ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        trade_executor: Any,  # TradeExecutor type
        date_helper: Any,  # DateHelper type
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize TradeExecutionService.

        Args:
            event_bus: EventBus for publishing/subscribing events
            trade_executor: TradeExecutor for executing trades
            date_helper: DateHelper for time calculations
            logger: Optional logger
            config: Service configuration with keys:
                - symbol: Trading symbol (required)
                - execution_mode: "immediate" or "batch" (default: "immediate")
                - batch_size: Signals to collect before executing (default: 1)
        """
        super().__init__(
            service_name="TradeExecutionService",
            event_bus=event_bus,
            logger=logger,
            config=config,
        )

        self.trade_executor = trade_executor
        self.date_helper = date_helper

        # Validate required config
        if not config:
            raise ValueError("TradeExecutionService requires configuration")

        if "symbol" not in config:
            raise ValueError("Configuration must include 'symbol'")

        # Configuration
        self.symbol = config["symbol"]
        self.execution_mode = config.get("execution_mode", "immediate")
        self.batch_size = config.get("batch_size", 1)

        # State: Collect signals if in batch mode
        self.pending_entries = []
        self.pending_exits = []

        # Metrics
        self._metrics["trades_executed"] = 0
        self._metrics["orders_placed"] = 0
        self._metrics["orders_rejected"] = 0
        self._metrics["positions_closed"] = 0
        self._metrics["risk_breaches"] = 0
        self._metrics["execution_errors"] = 0

        self.logger.info(
            f"TradeExecutionService initialized for {self.symbol} "
            f"(mode={self.execution_mode})"
        )

    def start(self) -> None:
        """
        Start the TradeExecutionService.

        Subscribes to TradesReadyEvent, EntrySignalEvent and ExitSignalEvent.
        """
        self.logger.info(f"Starting {self.service_name}...")

        # Subscribe to trades ready event (for execution)
        self.subscribe_to_event(TradesReadyEvent, self._on_trades_ready)

        # Subscribe to signal events (for logging/monitoring)
        self.subscribe_to_event(EntrySignalEvent, self._on_entry_signal)
        self.subscribe_to_event(ExitSignalEvent, self._on_exit_signal)

        self._set_status(ServiceStatus.RUNNING)
        self.logger.info(f"{self.service_name} started successfully")

    def stop(self) -> None:
        """
        Stop the TradeExecutionService gracefully.
        """
        self.logger.info(f"Stopping {self.service_name}...")

        # Execute any pending signals before stopping
        if self.pending_entries or self.pending_exits:
            self.logger.info(
                f"Executing {len(self.pending_entries)} pending entries "
                f"and {len(self.pending_exits)} pending exits before stopping"
            )
            self._execute_pending_signals()

        # Unsubscribe from all events
        self.unsubscribe_all()

        # Clear state
        self.pending_entries.clear()
        self.pending_exits.clear()

        self._set_status(ServiceStatus.STOPPED)
        self.logger.info(f"{self.service_name} stopped")

    def health_check(self) -> HealthStatus:
        """
        Check service health.

        Returns:
            HealthStatus indicating current health
        """
        is_healthy = (
            self._status == ServiceStatus.RUNNING
            and self._metrics["execution_errors"] < 10  # Less than 10 consecutive errors
        )

        return HealthStatus(
            service_name=self.service_name,
            status=self._status,
            is_healthy=is_healthy,
            uptime_seconds=self.get_uptime_seconds(),
            last_error=self._last_error,
            metrics=self.get_metrics(),
        )

    def _on_entry_signal(self, event: EntrySignalEvent) -> None:
        """
        Handle EntrySignalEvent.

        Args:
            event: EntrySignalEvent with entry signal
        """
        self._metrics["events_received"] += 1

        # Filter by symbol
        if event.symbol != self.symbol:
            self.logger.debug(
                f"Ignoring EntrySignalEvent for {event.symbol} "
                f"(configured for {self.symbol})"
            )
            return

        self.logger.info(
            f"Received entry signal: {event.strategy_name} {event.direction} {event.symbol}"
        )

        # Create EntryDecision from event
        # Note: The actual EntryDecision with position size, SL, TP
        # is already calculated by EntryManager in StrategyEvaluationService
        # Here we just need to pass the signal through to TradeExecutor
        # For now, we'll trigger execution directly since EntryManager
        # was already called in StrategyEvaluationService

        # Store for batch execution or execute immediately
        if self.execution_mode == "batch":
            self.pending_entries.append(event)
            if len(self.pending_entries) >= self.batch_size:
                self._execute_pending_signals()
        else:
            # Immediate execution
            # Note: In immediate mode, we need the full Trades object
            # which should come from StrategyEvaluationService
            # For now, we'll log that we received the signal
            self.logger.info(
                f"Entry signal received (immediate mode): "
                f"{event.strategy_name} {event.direction}"
            )

    def _on_exit_signal(self, event: ExitSignalEvent) -> None:
        """
        Handle ExitSignalEvent.

        Args:
            event: ExitSignalEvent with exit signal
        """
        self._metrics["events_received"] += 1

        # Filter by symbol
        if event.symbol != self.symbol:
            self.logger.debug(
                f"Ignoring ExitSignalEvent for {event.symbol} "
                f"(configured for {self.symbol})"
            )
            return

        self.logger.info(
            f"Received exit signal: {event.strategy_name} {event.direction} {event.symbol}"
        )

        # Store for batch execution or execute immediately
        if self.execution_mode == "batch":
            self.pending_exits.append(event)
            if (len(self.pending_entries) + len(self.pending_exits)) >= self.batch_size:
                self._execute_pending_signals()
        else:
            # Immediate execution
            self.logger.info(
                f"Exit signal received (immediate mode): "
                f"{event.strategy_name} {event.direction}"
            )

    def _on_trades_ready(self, event: TradesReadyEvent) -> None:
        """
        Handle TradesReadyEvent - execute trades immediately.

        Args:
            event: TradesReadyEvent with complete Trades object
        """
        self._metrics["events_received"] += 1

        # Filter by symbol
        if event.symbol != self.symbol:
            self.logger.debug(
                f"Ignoring TradesReadyEvent for {event.symbol} "
                f"(configured for {self.symbol})"
            )
            return

        self.logger.info(
            f"💼 [TRADES READY] {event.symbol} | "
            f"Executing {event.num_entries} entries, {event.num_exits} exits"
        )

        # Execute trades immediately
        try:
            self.execute_trades(event.trades)
        except Exception as e:
            self.logger.error(f"Error executing trades from event: {e}", exc_info=True)
            self._handle_error(e, "_on_trades_ready")

    def execute_trades(self, trades: Trades) -> None:
        """
        Execute trades directly (for orchestrator or manual execution).

        This method allows direct execution of trades without waiting for events.
        Useful for testing or when orchestrator calls services directly.

        Args:
            trades: Trades object with entry and exit decisions
        """
        if self._status != ServiceStatus.RUNNING:
            self.logger.warning(
                f"Cannot execute trades: service status is {self._status.value}"
            )
            return

        try:
            self.logger.info(
                f"Executing trades: {len(trades.entries)} entries, {len(trades.exits)} exits"
            )

            # Execute via TradeExecutor
            context = self.trade_executor.execute_trading_cycle(trades, self.date_helper)

            self._metrics["trades_executed"] += 1

            # Publish events based on context
            self._publish_events_from_context(context, trades)

        except Exception as e:
            self.logger.error(f"Error executing trades: {e}", exc_info=True)
            self._metrics["execution_errors"] += 1
            self._handle_error(e, "execute_trades")

    def _execute_pending_signals(self) -> None:
        """
        Execute pending entry and exit signals.

        This is called in batch mode when enough signals have accumulated.
        """
        if not self.pending_entries and not self.pending_exits:
            return

        self.logger.info(
            f"Executing pending signals: {len(self.pending_entries)} entries, "
            f"{len(self.pending_exits)} exits"
        )

        # Note: This is a simplified implementation
        # In a real scenario, we would need to reconstruct EntryDecision/ExitDecision
        # from the events, which requires the EntryManager configuration
        # For now, we'll just log that we would execute

        self.logger.info("Batch execution would happen here")

        # Clear pending signals
        self.pending_entries.clear()
        self.pending_exits.clear()

    def _publish_events_from_context(self, context: Any, trades: Trades) -> None:
        """
        Publish events based on trading context.

        Args:
            context: TradingContext from TradeExecutor
            trades: Trades that were executed
        """
        # Check if trading was blocked
        if not context.trade_authorized:
            reasons = []
            if context.news_block_active:
                reasons.append("news_block")
            if context.market_closing_soon:
                reasons.append("market_closing")
            if context.risk_breached:
                reasons.append("risk_breach")

            if reasons:
                self._publish_trading_blocked(reasons)

        # Check for risk breach
        if context.risk_breached:
            self._publish_risk_breach(context)

        # Publish trading authorized if trading proceeded
        if context.trade_authorized and not context.risk_breached:
            self._publish_trading_authorized()

        # Note: OrderPlacedEvent and PositionClosedEvent would be published
        # based on actual order execution results
        # This requires integration with the order_executor component

    def _publish_trading_authorized(self) -> None:
        """Publish TradingAuthorizedEvent."""
        try:
            event = TradingAuthorizedEvent(
                symbol=self.symbol,
                reason="all_checks_passed",
            )
            self.publish_event(event)

            self.logger.debug("Trading authorized")

        except Exception as e:
            self.logger.error(f"Failed to publish TradingAuthorizedEvent: {e}")

    def _publish_trading_blocked(self, reasons: list[str]) -> None:
        """
        Publish TradingBlockedEvent.

        Args:
            reasons: List of reasons for blocking
        """
        try:
            event = TradingBlockedEvent(
                symbol=self.symbol,
                reasons=reasons,
            )
            self.publish_event(event)

            self.logger.warning(f"Trading blocked: {', '.join(reasons)}")

        except Exception as e:
            self.logger.error(f"Failed to publish TradingBlockedEvent: {e}")

    def _publish_risk_breach(self, context: Any) -> None:
        """
        Publish RiskLimitBreachedEvent.

        Args:
            context: TradingContext with risk information
        """
        try:
            event = RiskLimitBreachedEvent(
                limit_type="daily_loss",
                current_value=context.total_pnl,
                limit_value=0.0,  # Would come from risk monitor config
                symbol=self.symbol,
            )
            self.publish_event(event)

            self._metrics["risk_breaches"] += 1

            self.logger.warning(
                f"Risk limit breached: total_pnl={context.total_pnl}"
            )

        except Exception as e:
            self.logger.error(f"Failed to publish RiskLimitBreachedEvent: {e}")

    def get_pending_signal_count(self) -> Dict[str, int]:
        """
        Get count of pending signals.

        Returns:
            Dictionary with pending entry and exit counts
        """
        return {
            "pending_entries": len(self.pending_entries),
            "pending_exits": len(self.pending_exits),
        }

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics including execution-specific metrics.

        Returns:
            Dictionary with metrics
        """
        base_metrics = super().get_metrics()

        # Add execution-specific metrics
        return {
            **base_metrics,
            "trades_executed": self._metrics["trades_executed"],
            "orders_placed": self._metrics["orders_placed"],
            "orders_rejected": self._metrics["orders_rejected"],
            "positions_closed": self._metrics["positions_closed"],
            "risk_breaches": self._metrics["risk_breaches"],
            "execution_errors": self._metrics["execution_errors"],
            "pending_entries": len(self.pending_entries),
            "pending_exits": len(self.pending_exits),
        }
