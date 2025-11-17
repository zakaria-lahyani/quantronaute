"""
API Service - Core service for managing API operations and EventBus integration.

This service provides the bridge between HTTP requests and the event-driven trading system.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime

from app.infrastructure.event_bus import EventBus
from app.events.strategy_events import EntrySignalEvent, ExitSignalEvent
from app.events.automation_events import (
    ToggleAutomationEvent,
    AutomationAction,
    AutomationStateChangedEvent
)


class APIService:
    """
    Core API service for managing event-driven operations.

    This service coordinates between HTTP requests and the EventBus,
    providing methods to:
    - Publish trading signals (entry/exit)
    - Control automation (enable/disable)
    - Query system state
    - Subscribe to events for monitoring

    The service acts as the bridge between the REST API and the
    event-driven trading system.
    """

    def __init__(
        self,
        event_bus: EventBus,
        logger: Optional[logging.Logger] = None,
        mt5_client: Optional[Any] = None,
        orchestrator: Optional[Any] = None
    ):
        """
        Initialize the API service.

        Args:
            event_bus: EventBus instance for publishing/subscribing to events
            logger: Optional logger instance
            mt5_client: Optional MT5Client instance for account/position queries
            orchestrator: Optional MultiSymbolOrchestrator instance for accessing services
        """
        self.event_bus = event_bus
        self.logger = logger or logging.getLogger(__name__)
        self._running = False
        self._startup_time: Optional[datetime] = None

        # Optional references to trading system components
        self.mt5_client = mt5_client
        self.orchestrator = orchestrator

        # Event subscriptions for monitoring
        self._subscription_ids: List[str] = []

        self.logger.info("APIService initialized")

    async def start(self):
        """
        Start the API service.

        Initializes EventBus subscriptions and marks the service as running.
        """
        if self._running:
            self.logger.warning("APIService already running")
            return

        self._running = True
        self._startup_time = datetime.now()

        # Subscribe to events for monitoring (optional - can be done per-request)
        # For now, we keep it lightweight - subscriptions happen on-demand

        self.logger.info("APIService started")

    async def stop(self):
        """
        Stop the API service.

        Cleans up EventBus subscriptions and resources.
        """
        if not self._running:
            self.logger.warning("APIService not running")
            return

        # Unsubscribe from all events
        for sub_id in self._subscription_ids:
            self.event_bus.unsubscribe(sub_id)

        self._subscription_ids.clear()
        self._running = False

        self.logger.info("APIService stopped")

    # ========================================================================
    # TRADING SIGNAL OPERATIONS
    # ========================================================================

    def trigger_entry_signal(
        self,
        symbol: str,
        direction: str,
        entry_price: Optional[float] = None
    ) -> None:
        """
        Trigger a manual entry signal.

        Publishes an EntrySignalEvent with strategy_name="manual" to the EventBus.
        The trading system will handle this exactly like an automated strategy signal.

        Args:
            symbol: Trading symbol (e.g., "XAUUSD", "BTCUSD")
            direction: Trade direction ("long" or "short")
            entry_price: Optional current market price for reference

        Example:
            ```python
            api_service.trigger_entry_signal("XAUUSD", "long", 2650.25)
            ```
        """
        event = EntrySignalEvent(
            strategy_name="manual",
            symbol=symbol.upper(),
            direction=direction.lower(),
            entry_price=entry_price
        )

        self.logger.info(
            f"Triggering manual entry signal: {symbol} {direction} "
            f"@ {entry_price if entry_price else 'market'}"
        )

        self.event_bus.publish(event)

    def execute_manual_order(
        self,
        symbol: str,
        direction: str,
        volume: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        comment: str = "manual_api"
    ) -> Optional[Dict[str, Any]]:
        """
        Execute a manual order directly through MT5Client.

        This bypasses the event-driven architecture and directly places the order.
        Use this for manual trading when the API is not connected to the trading system.

        Args:
            symbol: Trading symbol (e.g., "XAUUSD", "BTCUSD")
            direction: Trade direction ("long" or "short")
            volume: Trade volume/lot size
            stop_loss: Optional stop loss price
            take_profit: Optional take profit price
            comment: Order comment (default: "manual_api")

        Returns:
            Order execution result or None if MT5Client not available

        Example:
            ```python
            result = api_service.execute_manual_order(
                symbol="XAUUSD",
                direction="long",
                volume=0.1,
                stop_loss=2640.0,
                take_profit=2670.0
            )
            ```
        """
        if self.mt5_client is None:
            self.logger.error("MT5Client not available for manual order execution")
            return None

        try:
            self.logger.info(
                f"Executing manual {direction} order: {symbol} volume={volume} "
                f"SL={stop_loss} TP={take_profit}"
            )

            # Execute buy or sell order based on direction
            if direction.lower() == "long":
                result = self.mt5_client.orders.create_buy_order(
                    symbol=symbol.upper(),
                    volume=volume,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=comment,
                    magic=999999  # Use a specific magic number for manual API orders
                )
            elif direction.lower() == "short":
                result = self.mt5_client.orders.create_sell_order(
                    symbol=symbol.upper(),
                    volume=volume,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    comment=comment,
                    magic=999999
                )
            else:
                self.logger.error(f"Invalid direction: {direction}")
                return None

            self.logger.info(f"Manual order result: {result}")
            return result

        except Exception as e:
            self.logger.error(f"Error executing manual order: {e}")
            return None

    def trigger_exit_signal(
        self,
        symbol: str,
        direction: str,
        reason: str = "manual"
    ) -> None:
        """
        Trigger a manual exit signal.

        Publishes an ExitSignalEvent with strategy_name="manual" to close positions.

        Args:
            symbol: Trading symbol
            direction: Position direction to exit ("long" or "short")
            reason: Reason for exit (default: "manual")

        Example:
            ```python
            api_service.trigger_exit_signal("XAUUSD", "long", "manual_close")
            ```
        """
        event = ExitSignalEvent(
            strategy_name="manual",
            symbol=symbol.upper(),
            direction=direction.lower(),
            reason=reason
        )

        self.logger.info(
            f"Triggering manual exit signal: {symbol} {direction} (reason: {reason})"
        )

        self.event_bus.publish(event)

    # ========================================================================
    # AUTOMATION CONTROL OPERATIONS
    # ========================================================================

    def enable_automation(self) -> None:
        """
        Enable automated trading.

        Publishes ToggleAutomationEvent to activate automated strategies.
        """
        event = ToggleAutomationEvent(
            action=AutomationAction.ENABLE,
            reason="API request",
            requested_by="api"
        )

        self.logger.info("Enabling automated trading via API")

        self.event_bus.publish(event)

    def disable_automation(self) -> None:
        """
        Disable automated trading.

        Publishes ToggleAutomationEvent to deactivate automated strategies.
        Manual trading via API will still work.
        """
        event = ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="API request",
            requested_by="api"
        )

        self.logger.info("Disabling automated trading via API")

        self.event_bus.publish(event)

    def query_automation_status(self) -> None:
        """
        Query current automation status.

        Publishes ToggleAutomationEvent to request current automation state.
        The response will be published as an AutomationStateChangedEvent.
        """
        event = ToggleAutomationEvent(
            action=AutomationAction.QUERY,
            reason="Status query",
            requested_by="api"
        )

        self.logger.debug("Querying automation status")

        self.event_bus.publish(event)

    # ========================================================================
    # SYSTEM MONITORING
    # ========================================================================

    def get_event_bus_metrics(self) -> Dict[str, Any]:
        """
        Get EventBus metrics for system monitoring.

        Returns:
            Dictionary containing EventBus metrics:
            - events_published: Total events published
            - events_delivered: Total events delivered
            - handler_errors: Total handler errors
            - subscription_count: Active subscriptions
            - event_history_size: Size of event history
        """
        return self.event_bus.get_metrics()

    def get_service_status(self) -> Dict[str, Any]:
        """
        Get API service status.

        Returns:
            Dictionary containing service status:
            - running: Whether service is running
            - uptime_seconds: Service uptime in seconds
            - startup_time: When service started (ISO format)
            - event_bus_metrics: EventBus metrics
        """
        uptime_seconds = None
        startup_time_str = None

        if self._startup_time:
            uptime = datetime.now() - self._startup_time
            uptime_seconds = uptime.total_seconds()
            startup_time_str = self._startup_time.isoformat()

        return {
            "running": self._running,
            "uptime_seconds": uptime_seconds,
            "startup_time": startup_time_str,
            "event_bus_metrics": self.get_event_bus_metrics()
        }

    # ========================================================================
    # EVENT HISTORY & DEBUGGING
    # ========================================================================

    def get_recent_events(
        self,
        event_type: Optional[type] = None,
        limit: int = 100
    ) -> List[Any]:
        """
        Get recent events from EventBus history.

        Useful for debugging and monitoring what events have been published.

        Args:
            event_type: Optional event type to filter by
            limit: Maximum number of events to return

        Returns:
            List of recent events
        """
        return self.event_bus.get_event_history(event_type, limit)

    # ========================================================================
    # ACCOUNT DATA RETRIEVAL
    # ========================================================================

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        Get full account information from MT5Client.

        Returns:
            Account information dict or None if MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for account info query")
            return None

        try:
            return self.mt5_client.account.get_account_info()
        except Exception as e:
            self.logger.error(f"Error retrieving account info: {e}")
            return None

    def get_account_summary(self) -> Optional[Dict[str, Any]]:
        """
        Get account summary with key metrics.

        Returns:
            Account summary dict or None if MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for account summary query")
            return None

        try:
            return self.mt5_client.account.get_account_summary()
        except Exception as e:
            self.logger.error(f"Error retrieving account summary: {e}")
            return None

    def get_account_balance(self) -> Optional[float]:
        """
        Get current account balance.

        Returns:
            Account balance or None if MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for balance query")
            return None

        try:
            return self.mt5_client.account.get_balance()
        except Exception as e:
            self.logger.error(f"Error retrieving account balance: {e}")
            return None

    def get_account_equity(self) -> Optional[Dict[str, float]]:
        """
        Get current account equity.

        Returns:
            Equity dict or None if MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for equity query")
            return None

        try:
            return self.mt5_client.account.get_equity()
        except Exception as e:
            self.logger.error(f"Error retrieving account equity: {e}")
            return None

    def get_margin_info(self) -> Optional[Dict[str, float]]:
        """
        Get margin information.

        Returns:
            Margin info dict or None if MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for margin query")
            return None

        try:
            return self.mt5_client.account.get_margin_info()
        except Exception as e:
            self.logger.error(f"Error retrieving margin info: {e}")
            return None

    # ========================================================================
    # POSITION DATA RETRIEVAL
    # ========================================================================

    def get_open_positions(self) -> Optional[List[Dict[str, Any]]]:
        """
        Get all currently open trading positions.

        Returns:
            List of position dicts or None if MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for positions query")
            return None

        try:
            positions = self.mt5_client.positions.get_open_positions()
            # Convert Position models to dicts
            return [pos.model_dump() for pos in positions]
        except Exception as e:
            self.logger.error(f"Error retrieving open positions: {e}")
            return None

    def get_positions_by_symbol(self, symbol: str) -> Optional[List[Dict[str, Any]]]:
        """
        Get all open positions filtered by trading symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of position dicts or None if MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for positions query")
            return None

        try:
            positions = self.mt5_client.positions.get_positions_by_symbol(symbol.upper())
            return [pos.model_dump() for pos in positions]
        except Exception as e:
            self.logger.error(f"Error retrieving positions for {symbol}: {e}")
            return None

    def get_position_by_ticket(self, ticket: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific open position by its ticket number.

        Args:
            ticket: Unique ticket ID of the position

        Returns:
            Position dict or None if not found or MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for position query")
            return None

        try:
            position = self.mt5_client.positions.get_position_by_ticket(ticket)
            return position.model_dump() if position else None
        except Exception as e:
            self.logger.error(f"Error retrieving position {ticket}: {e}")
            return None

    # ========================================================================
    # POSITION HISTORY DATA RETRIEVAL
    # ========================================================================

    def get_closed_positions(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get all closed positions from history.

        Args:
            start: Optional start datetime (ISO format)
            end: Optional end datetime (ISO format)

        Returns:
            List of closed position dicts or None if MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for closed positions query")
            return None

        try:
            return self.mt5_client.history.get_closed_positions(start=start, end=end)
        except Exception as e:
            self.logger.error(f"Error retrieving closed positions: {e}")
            return None

    def get_closed_positions_by_symbol(
        self,
        symbol: str,
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get closed positions filtered by symbol.

        Args:
            symbol: Trading symbol
            start: Optional start datetime (ISO format)
            end: Optional end datetime (ISO format)

        Returns:
            List of closed position dicts or None if MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for closed positions query")
            return None

        try:
            return self.mt5_client.history.get_closed_positions_by_symbol(
                symbol.upper(),
                start=start,
                end=end
            )
        except Exception as e:
            self.logger.error(f"Error retrieving closed positions for {symbol}: {e}")
            return None

    def get_closed_position_by_ticket(self, ticket: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific closed position by ticket number.

        Args:
            ticket: Position ticket number

        Returns:
            Closed position dict or None if not found or MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for closed position query")
            return None

        try:
            return self.mt5_client.history.get_closed_position_by_ticket(ticket)
        except Exception as e:
            self.logger.error(f"Error retrieving closed position {ticket}: {e}")
            return None

    def get_trading_statistics(
        self,
        start: Optional[str] = None,
        end: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Get trading statistics from closed positions.

        Args:
            start: Optional start datetime (ISO format)
            end: Optional end datetime (ISO format)

        Returns:
            Dictionary with trading statistics or None if MT5Client not available
        """
        if self.mt5_client is None:
            self.logger.warning("MT5Client not available for trading statistics query")
            return None

        try:
            return self.mt5_client.history.get_trading_statistics(start=start, end=end)
        except Exception as e:
            self.logger.error(f"Error retrieving trading statistics: {e}")
            return None

    # ========================================================================
    # STRATEGY EVALUATION DATA RETRIEVAL
    # ========================================================================

    def get_strategy_service(self, symbol: str):
        """
        Get StrategyEvaluationService for a specific symbol.

        Args:
            symbol: Trading symbol

        Returns:
            StrategyEvaluationService instance or None if not available
        """
        if self.orchestrator is None:
            self.logger.warning(f"Orchestrator not available for strategy query: {symbol}")
            return None

        try:
            return self.orchestrator.get_service(symbol, "strategy_evaluation")
        except Exception as e:
            self.logger.error(f"Error accessing strategy service for {symbol}: {e}")
            return None

    def get_available_strategies(self, symbol: str) -> Optional[List[str]]:
        """
        Get list of available strategy names for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            List of strategy names or None if not available
        """
        strategy_service = self.get_strategy_service(symbol)
        if strategy_service is None:
            return None

        try:
            return strategy_service.get_available_strategies()
        except Exception as e:
            self.logger.error(f"Error retrieving available strategies for {symbol}: {e}")
            return None

    def get_strategy_info(self, symbol: str, strategy_name: str) -> Optional[Dict[str, Any]]:
        """
        Get strategy information for a specific symbol and strategy.

        Args:
            symbol: Trading symbol
            strategy_name: Name of the strategy

        Returns:
            Strategy info dict or None if not available
        """
        strategy_service = self.get_strategy_service(symbol)
        if strategy_service is None:
            return None

        try:
            strategy_info = strategy_service.get_strategy_info(strategy_name)
            if strategy_info is None:
                return None

            # Convert to dict if it's an object
            if hasattr(strategy_info, 'model_dump'):
                return strategy_info.model_dump()
            elif hasattr(strategy_info, '__dict__'):
                return strategy_info.__dict__
            else:
                return {"info": str(strategy_info)}
        except Exception as e:
            self.logger.error(f"Error retrieving strategy info for {symbol}/{strategy_name}: {e}")
            return None

    def get_strategy_metrics(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get strategy evaluation metrics for a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Strategy metrics dict or None if not available
        """
        strategy_service = self.get_strategy_service(symbol)
        if strategy_service is None:
            return None

        try:
            return strategy_service.get_metrics()
        except Exception as e:
            self.logger.error(f"Error retrieving strategy metrics for {symbol}: {e}")
            return None

    # ========================================================================
    # INDICATOR DATA RETRIEVAL
    # ========================================================================

    def get_indicator_service(self, symbol: str):
        """
        Get IndicatorCalculationService for a specific symbol.

        Args:
            symbol: Trading symbol

        Returns:
            IndicatorCalculationService instance or None if not available
        """
        if self.orchestrator is None:
            self.logger.warning(f"Orchestrator not available for indicator query: {symbol}")
            return None

        try:
            # Access the indicator service for this symbol from orchestrator
            return self.orchestrator.get_service(symbol, "indicator_calculation")
        except Exception as e:
            self.logger.error(f"Error accessing indicator service for {symbol}: {e}")
            return None

    def get_latest_indicators(self, symbol: str, timeframe: str) -> Optional[Dict[str, Any]]:
        """
        Get latest indicator values for a symbol and timeframe.

        Args:
            symbol: Trading symbol
            timeframe: Timeframe (e.g., "M1", "H1", "D1")

        Returns:
            Dictionary of indicator values or None if not available
        """
        indicator_service = self.get_indicator_service(symbol)
        if indicator_service is None:
            return None

        try:
            latest_row = indicator_service.get_latest_row(timeframe)
            if latest_row is None:
                self.logger.warning(f"No indicator data available for {symbol} {timeframe}")
                return None

            # Convert pandas Series to dict
            return latest_row.to_dict()
        except Exception as e:
            self.logger.error(f"Error retrieving indicators for {symbol} {timeframe}: {e}")
            return None

    def get_all_indicators_for_symbol(self, symbol: str) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        Get latest indicator values for all timeframes of a symbol.

        Args:
            symbol: Trading symbol

        Returns:
            Dictionary mapping timeframe -> indicator values
        """
        indicator_service = self.get_indicator_service(symbol)
        if indicator_service is None:
            return None

        try:
            # Get configured timeframes from the service
            timeframes = indicator_service.config.get("timeframes", [])

            result = {}
            for tf in timeframes:
                indicators = self.get_latest_indicators(symbol, tf)
                if indicators:
                    result[tf] = indicators

            return result if result else None
        except Exception as e:
            self.logger.error(f"Error retrieving all indicators for {symbol}: {e}")
            return None

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running
