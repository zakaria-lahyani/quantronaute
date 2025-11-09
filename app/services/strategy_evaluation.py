"""
Strategy Evaluation Service.

This service wraps the StrategyEngine and EntryManager and publishes strategy events.
It is responsible for:
- Subscribing to IndicatorsCalculatedEvent
- Evaluating strategies with enriched market data
- Generating entry and exit signals
- Publishing EntrySignalEvent and ExitSignalEvent
- Handling evaluation errors gracefully
"""

import logging
from typing import Dict, Optional, Any
from collections import deque

from app.services.base import EventDrivenService, ServiceStatus, HealthStatus
from app.infrastructure.event_bus import EventBus
from app.events.indicator_events import IndicatorsCalculatedEvent
from app.events.strategy_events import (
    EntrySignalEvent,
    ExitSignalEvent,
    TradesReadyEvent,
    StrategyEvaluationErrorEvent,
)


class StrategyEvaluationService(EventDrivenService):
    """
    Service for evaluating trading strategies and generating signals.

    This service wraps the StrategyEngine and EntryManager and is responsible for:
    - Subscribing to IndicatorsCalculatedEvent
    - Evaluating strategies with enriched data (indicators + regime)
    - Generating entry and exit signals via EntryManager
    - Publishing EntrySignalEvent when entry signal is generated
    - Publishing ExitSignalEvent when exit signal is generated
    - Publishing StrategyEvaluationErrorEvent when errors occur
    - Tracking evaluation metrics

    Configuration:
        symbol: Trading symbol (e.g., "EURUSD") - for event filtering
        min_rows_required: Minimum rows required before evaluating (default: 3)

    Example:
        ```python
        # Create strategy engine from configs
        strategy_engine = StrategyEngineFactory.create_engine(
            config_paths=["strategy1.yaml", "strategy2.yaml"]
        )

        # Get strategies dict for entry manager
        strategies = {
            name: strategy_engine.get_strategy_info(name)
            for name in strategy_engine.list_available_strategies()
        }

        # Create entry manager
        entry_manager = EntryManager(
            strategies=strategies,
            symbol="EURUSD",
            pip_value=10000.0
        )

        service = StrategyEvaluationService(
            event_bus=event_bus,
            strategy_engine=strategy_engine,
            entry_manager=entry_manager,
            config={
                "symbol": "EURUSD",
                "min_rows_required": 3
            }
        )

        service.start()
        # Service now listens for IndicatorsCalculatedEvent and evaluates automatically
        ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        strategy_engine: Any,  # StrategyEngine type from strategy_builder
        entry_manager: Any,  # EntryManager type
        client: Optional[Any] = None,  # MT5 Client for fetching account balance
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize StrategyEvaluationService.

        Args:
            event_bus: EventBus for publishing/subscribing events
            strategy_engine: StrategyEngine for evaluating strategies
            entry_manager: EntryManager for generating trade decisions
            client: Optional MT5 client for fetching account balance
            logger: Optional logger
            config: Service configuration with keys:
                - symbol: Trading symbol (required)
                - min_rows_required: Min rows for evaluation (default: 3)
        """
        super().__init__(
            service_name="StrategyEvaluationService",
            event_bus=event_bus,
            logger=logger,
            config=config,
        )

        self.strategy_engine = strategy_engine
        self.entry_manager = entry_manager
        self.client = client

        # Validate required config
        if not config:
            raise ValueError("StrategyEvaluationService requires configuration")

        if "symbol" not in config:
            raise ValueError("Configuration must include 'symbol'")

        # Configuration
        self.symbol = config["symbol"]
        self.min_rows_required = config.get("min_rows_required", 3)

        # Metrics
        self._metrics["strategies_evaluated"] = 0
        self._metrics["entry_signals_generated"] = 0
        self._metrics["exit_signals_generated"] = 0
        self._metrics["evaluation_errors"] = 0

        self.logger.info(
            f"StrategyEvaluationService initialized for {self.symbol} "
            f"(min_rows={self.min_rows_required})"
        )

    def start(self) -> None:
        """
        Start the StrategyEvaluationService.

        Subscribes to IndicatorsCalculatedEvent.
        """
        self.logger.info(f"Starting {self.service_name}...")

        # Subscribe to IndicatorsCalculatedEvent
        self.subscribe_to_event(IndicatorsCalculatedEvent, self._on_indicators_calculated)

        self._set_status(ServiceStatus.RUNNING)
        self.logger.info(f"{self.service_name} started successfully")

    def stop(self) -> None:
        """
        Stop the StrategyEvaluationService gracefully.
        """
        self.logger.info(f"Stopping {self.service_name}...")

        # Unsubscribe from all events
        self.unsubscribe_all()

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
            and self._metrics["evaluation_errors"] < 10  # Less than 10 consecutive errors
        )

        return HealthStatus(
            service_name=self.service_name,
            status=self._status,
            is_healthy=is_healthy,
            uptime_seconds=self.get_uptime_seconds(),
            last_error=self._last_error,
            metrics=self.get_metrics(),
        )

    def _on_indicators_calculated(self, event: IndicatorsCalculatedEvent) -> None:
        """
        Handle IndicatorsCalculatedEvent.

        When indicators are calculated:
        1. Filter by symbol
        2. Check if sufficient data for evaluation
        3. Evaluate strategies with recent_rows
        4. Generate entry/exit signals via EntryManager
        5. Publish EntrySignalEvent and ExitSignalEvent

        Args:
            event: IndicatorsCalculatedEvent with enriched data
        """
        self._metrics["events_received"] += 1

        # Filter by symbol
        if event.symbol != self.symbol:
            self.logger.debug(
                f"Ignoring IndicatorsCalculatedEvent for {event.symbol} "
                f"(configured for {self.symbol})"
            )
            return

        # Check if we have sufficient data
        if not self._has_sufficient_data(event.recent_rows):
            self.logger.debug(
                f"Insufficient data for strategy evaluation (need {self.min_rows_required} rows)"
            )
            return

        # Evaluate strategies
        try:
            self._evaluate_strategies(event.recent_rows)

        except Exception as e:
            self.logger.error(
                f"Error evaluating strategies for {event.symbol}: {e}",
                exc_info=True,
            )
            self._publish_evaluation_error(e)
            self._handle_error(e, "_on_indicators_calculated")

    def _has_sufficient_data(self, recent_rows: Dict[str, deque]) -> bool:
        """
        Check if recent_rows has sufficient data for strategy evaluation.

        Args:
            recent_rows: Dictionary mapping timeframe to deque of rows

        Returns:
            True if sufficient data available
        """
        if not recent_rows:
            return False

        # Check if any timeframe has minimum required rows
        for tf, rows in recent_rows.items():
            if len(rows) >= self.min_rows_required:
                return True

        return False

    def _evaluate_strategies(self, recent_rows: Dict[str, deque]) -> None:
        """
        Evaluate strategies with enriched market data and generate signals.

        Args:
            recent_rows: Dictionary mapping timeframe to deque of enriched rows
        """
        # Log available data
        data_summary = {tf: len(rows) for tf, rows in recent_rows.items()}
        self.logger.info(f"🎲 [STRATEGY START] {self.symbol} | Available rows per TF: {data_summary}")

        # Step 1: Evaluate strategies using strategy engine
        strategy_results = self.strategy_engine.evaluate(recent_rows)

        self._metrics["strategies_evaluated"] += 1

        # Log strategy evaluation results
        self.logger.info(
            f"📈 [STRATEGY EVAL] {self.symbol} | "
            f"Evaluated {len(strategy_results.strategies)} strategies"
        )

        # Step 2: Get account balance
        account_balance = None
        if self.client:
            try:
                account_balance = self.client.account.get_balance()
            except Exception as e:
                self.logger.warning(f"Failed to fetch account balance: {e}")

        # Step 3: Generate trade decisions using entry manager
        trades = self.entry_manager.manage_trades(
            strategy_results.strategies,
            recent_rows,
            account_balance=account_balance
        )

        # Log trade generation results
        self.logger.info(
            f"💡 [TRADE DECISIONS] {self.symbol} | "
            f"Entries: {len(trades.entries)}, Exits: {len(trades.exits)}"
        )

        # Step 3: Publish TradesReadyEvent with complete trades object
        if trades.entries or trades.exits:
            self._publish_trades_ready(trades)

        # Step 4: Publish individual entry signals (for monitoring/logging)
        for entry_decision in trades.entries:
            self._publish_entry_signal(entry_decision)

        # Step 5: Publish individual exit signals (for monitoring/logging)
        for exit_decision in trades.exits:
            self._publish_exit_signal(exit_decision)

    def _publish_trades_ready(self, trades: Any) -> None:
        """
        Publish TradesReadyEvent with complete trades object.

        Args:
            trades: Trades object from EntryManager
        """
        try:
            trades_event = TradesReadyEvent(
                symbol=self.symbol,
                trades=trades,
                num_entries=len(trades.entries),
                num_exits=len(trades.exits),
            )
            self.publish_event(trades_event)

            self.logger.info(
                f"📦 [TRADES READY] {self.symbol} | "
                f"Entries: {len(trades.entries)}, Exits: {len(trades.exits)}"
            )

        except Exception as e:
            self.logger.error(f"Failed to publish TradesReadyEvent: {e}")

    def _publish_entry_signal(self, entry_decision: Any) -> None:
        """
        Publish EntrySignalEvent from an entry decision.

        Args:
            entry_decision: EntryDecision object from EntryManager
        """
        try:
            # Extract price from entry decision
            entry_price = getattr(entry_decision, 'entry_price', None)

            entry_event = EntrySignalEvent(
                strategy_name=entry_decision.strategy_name,
                symbol=entry_decision.symbol,
                direction=entry_decision.direction,
                entry_price=entry_price,
            )
            self.publish_event(entry_event)

            self._metrics["entry_signals_generated"] += 1

            self.logger.info(
                f"🟢 [ENTRY SIGNAL] {entry_decision.strategy_name} | "
                f"{entry_decision.direction} {entry_decision.symbol} @ {entry_price}"
            )

        except Exception as e:
            self.logger.error(f"Failed to publish EntrySignalEvent: {e}")

    def _publish_exit_signal(self, exit_decision: Any) -> None:
        """
        Publish ExitSignalEvent from an exit decision.

        Args:
            exit_decision: ExitDecision object from EntryManager
        """
        try:
            exit_event = ExitSignalEvent(
                strategy_name=exit_decision.strategy_name,
                symbol=exit_decision.symbol,
                direction=exit_decision.direction,
                reason="signal",  # Default reason
            )
            self.publish_event(exit_event)

            self._metrics["exit_signals_generated"] += 1

            self.logger.info(
                f"🔴 [EXIT SIGNAL] {exit_decision.strategy_name} | "
                f"{exit_decision.direction} {exit_decision.symbol}"
            )

        except Exception as e:
            self.logger.error(f"Failed to publish ExitSignalEvent: {e}")

    def _publish_evaluation_error(self, exception: Exception) -> None:
        """
        Publish StrategyEvaluationErrorEvent.

        Args:
            exception: Exception that occurred
        """
        try:
            error_event = StrategyEvaluationErrorEvent(
                strategy_name="unknown",  # Don't know which strategy failed
                symbol=self.symbol,
                error=str(exception),
                exception=exception,
            )
            self.publish_event(error_event)
            self._metrics["evaluation_errors"] += 1

        except Exception as e:
            self.logger.error(f"Failed to publish StrategyEvaluationErrorEvent: {e}")

    def get_available_strategies(self) -> list[str]:
        """
        Get list of available strategy names.

        Returns:
            List of strategy names
        """
        try:
            return self.strategy_engine.list_available_strategies()
        except Exception as e:
            self.logger.error(f"Error getting available strategies: {e}")
            return []

    def get_strategy_info(self, strategy_name: str) -> Optional[Any]:
        """
        Get strategy information.

        Args:
            strategy_name: Name of the strategy

        Returns:
            Strategy info or None
        """
        try:
            return self.strategy_engine.get_strategy_info(strategy_name)
        except Exception as e:
            self.logger.error(f"Error getting strategy info for {strategy_name}: {e}")
            return None

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics including strategy-specific metrics.

        Returns:
            Dictionary with metrics
        """
        base_metrics = super().get_metrics()

        # Add strategy-specific metrics
        return {
            **base_metrics,
            "strategies_evaluated": self._metrics["strategies_evaluated"],
            "entry_signals_generated": self._metrics["entry_signals_generated"],
            "exit_signals_generated": self._metrics["exit_signals_generated"],
            "evaluation_errors": self._metrics["evaluation_errors"],
        }
