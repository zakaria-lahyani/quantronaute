"""
Base class for event-driven services.

All services inherit from EventDrivenService and implement the service lifecycle.
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

from app.infrastructure.event_bus import EventBus
from app.events.base import Event


class ServiceStatus(Enum):
    """Service status enumeration."""
    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class HealthStatus:
    """
    Health status for a service.

    Attributes:
        service_name: Name of the service
        status: Current service status
        is_healthy: Whether the service is healthy
        uptime_seconds: How long the service has been running
        last_error: Last error message (if any)
        metrics: Service-specific metrics
    """
    service_name: str
    status: ServiceStatus
    is_healthy: bool
    uptime_seconds: float = 0.0
    last_error: Optional[str] = None
    metrics: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize metrics if None."""
        if self.metrics is None:
            self.metrics = {}


class EventDrivenService(ABC):
    """
    Abstract base class for event-driven services.

    All services must implement:
    - start(): Initialize and start the service
    - stop(): Gracefully stop the service
    - health_check(): Return current health status

    Services have access to:
    - EventBus: For publishing and subscribing to events
    - Logger: For logging
    - Config: Service-specific configuration

    Example:
        ```python
        class MyService(EventDrivenService):
            def start(self):
                self.event_bus.subscribe(NewCandleEvent, self.on_new_candle)
                self.logger.info(f"{self.service_name} started")

            def stop(self):
                self.logger.info(f"{self.service_name} stopped")

            def health_check(self) -> HealthStatus:
                return HealthStatus(
                    service_name=self.service_name,
                    status=self._status,
                    is_healthy=self._status == ServiceStatus.RUNNING
                )

            def on_new_candle(self, event: NewCandleEvent):
                # Handle the event
                self.publish_event(IndicatorsCalculatedEvent(...))
        ```
    """

    def __init__(
        self,
        service_name: str,
        event_bus: EventBus,
        logger: Optional[logging.Logger] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize the service.

        Args:
            service_name: Name of the service (for logging and identification)
            event_bus: EventBus instance for publishing/subscribing
            logger: Optional logger (creates one if not provided)
            config: Optional service-specific configuration
        """
        self.service_name = service_name
        self.event_bus = event_bus
        self.logger = logger or logging.getLogger(f"services.{service_name}")
        self.config = config or {}

        # Service state
        self._status = ServiceStatus.INITIALIZING
        self._start_time: Optional[datetime] = None
        self._last_error: Optional[str] = None

        # Metrics
        self._metrics = {
            "events_published": 0,
            "events_received": 0,
            "errors": 0,
        }

        # Subscription IDs for cleanup
        self._subscription_ids: list[str] = []

    @abstractmethod
    def start(self) -> None:
        """
        Start the service.

        This method should:
        1. Subscribe to required events
        2. Initialize any resources
        3. Set status to RUNNING

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def stop(self) -> None:
        """
        Stop the service gracefully.

        This method should:
        1. Unsubscribe from events
        2. Clean up resources
        3. Set status to STOPPED

        Must be implemented by subclasses.
        """
        pass

    @abstractmethod
    def health_check(self) -> HealthStatus:
        """
        Check service health.

        Returns:
            HealthStatus indicating current service health

        Must be implemented by subclasses.
        """
        pass

    def publish_event(self, event: Event) -> None:
        """
        Publish an event to the EventBus.

        This is a convenience method that also tracks metrics.

        Args:
            event: Event to publish
        """
        try:
            self.event_bus.publish(event)
            self._metrics["events_published"] += 1
        except Exception as e:
            self._metrics["errors"] += 1
            self.logger.error(f"Error publishing event {type(event).__name__}: {e}")
            raise

    def subscribe_to_event(
        self,
        event_type: type[Event],
        handler: callable,
    ) -> str:
        """
        Subscribe to an event type.

        This is a convenience method that tracks subscription IDs for cleanup.

        Args:
            event_type: Type of event to subscribe to
            handler: Handler function

        Returns:
            Subscription ID
        """
        subscription_id = self.event_bus.subscribe(event_type, handler)
        self._subscription_ids.append(subscription_id)
        return subscription_id

    def unsubscribe_all(self) -> None:
        """Unsubscribe from all events."""
        for subscription_id in self._subscription_ids:
            self.event_bus.unsubscribe(subscription_id)
        self._subscription_ids.clear()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get service metrics.

        Returns:
            Dictionary containing service metrics
        """
        return {
            **self._metrics,
            "uptime_seconds": self.get_uptime_seconds(),
            "status": self._status.value,
        }

    def get_uptime_seconds(self) -> float:
        """
        Get service uptime in seconds.

        Returns:
            Uptime in seconds, or 0 if not started
        """
        if self._start_time is None:
            return 0.0
        return (datetime.now() - self._start_time).total_seconds()

    def _set_status(self, status: ServiceStatus) -> None:
        """
        Set service status.

        Args:
            status: New status
        """
        old_status = self._status
        self._status = status

        if status == ServiceStatus.RUNNING and self._start_time is None:
            self._start_time = datetime.now()

        self.logger.debug(f"{self.service_name} status changed: {old_status.value} -> {status.value}")

    def _handle_error(self, error: Exception, context: str = "") -> None:
        """
        Handle an error in the service.

        Args:
            error: The exception that occurred
            context: Optional context about where the error occurred
        """
        self._metrics["errors"] += 1
        self._last_error = str(error)
        self._status = ServiceStatus.ERROR

        error_msg = f"Error in {self.service_name}"
        if context:
            error_msg += f" ({context})"
        error_msg += f": {error}"

        self.logger.error(error_msg, exc_info=True)

    def __repr__(self) -> str:
        """String representation of the service."""
        return (
            f"{self.__class__.__name__}("
            f"name={self.service_name}, "
            f"status={self._status.value}, "
            f"uptime={self.get_uptime_seconds():.1f}s"
            f")"
        )
