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
    AutomationEnabledEvent,
    AutomationDisabledEvent,
    AutomationStatusQueryEvent
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
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the API service.

        Args:
            event_bus: EventBus instance for publishing/subscribing to events
            logger: Optional logger instance
        """
        self.event_bus = event_bus
        self.logger = logger or logging.getLogger(__name__)
        self._running = False
        self._startup_time: Optional[datetime] = None

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

        Publishes AutomationEnabledEvent to activate automated strategies.
        """
        event = AutomationEnabledEvent(source="api")

        self.logger.info("Enabling automated trading via API")

        self.event_bus.publish(event)

    def disable_automation(self) -> None:
        """
        Disable automated trading.

        Publishes AutomationDisabledEvent to deactivate automated strategies.
        Manual trading via API will still work.
        """
        event = AutomationDisabledEvent(source="api")

        self.logger.info("Disabling automated trading via API")

        self.event_bus.publish(event)

    def query_automation_status(self) -> None:
        """
        Query current automation status.

        Publishes AutomationStatusQueryEvent to request current automation state.
        The response will be published as an AutomationStatusEvent.
        """
        event = AutomationStatusQueryEvent(source="api")

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

    @property
    def is_running(self) -> bool:
        """Check if service is running."""
        return self._running
