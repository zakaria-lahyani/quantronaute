"""
EventBus implementation for publish/subscribe event communication.

The EventBus allows services to communicate through events without
directly depending on each other.
"""

import logging
from collections import defaultdict, deque
from typing import Type, Callable, Dict, List, Optional, Any, Deque
from datetime import datetime

from app.events.base import Event, EventHandler


class EventBus:
    """
    Central event bus for publish/subscribe communication.

    The EventBus maintains subscriptions and delivers events to registered handlers.
    It supports:
    - Event subscription by event type
    - Synchronous event delivery
    - Event history for debugging
    - Handler error isolation (one handler's error doesn't affect others)
    - Metrics tracking

    Example:
        ```python
        event_bus = EventBus()

        # Subscribe to events
        def handle_new_candle(event: NewCandleEvent):
            print(f"New candle: {event.symbol} {event.timeframe}")

        subscription_id = event_bus.subscribe(NewCandleEvent, handle_new_candle)

        # Publish events
        event_bus.publish(NewCandleEvent(symbol="EURUSD", timeframe="1", bar=...))

        # Unsubscribe
        event_bus.unsubscribe(subscription_id)
        ```
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        event_history_limit: int = 1000,
        log_all_events: bool = False,
    ):
        """
        Initialize the EventBus.

        Args:
            logger: Optional logger for event logging
            event_history_limit: Maximum number of events to keep in history
            log_all_events: Whether to log every published event
        """
        self.logger = logger or logging.getLogger(__name__)
        self.event_history_limit = event_history_limit
        self.log_all_events = log_all_events

        # Subscriptions: event_type -> list of (subscription_id, handler)
        self._subscriptions: Dict[Type[Event], List[tuple[str, EventHandler]]] = defaultdict(list)

        # Event history: deque of (timestamp, event)
        self._event_history: Deque[tuple[datetime, Event]] = deque(maxlen=event_history_limit)

        # Metrics
        self._metrics = {
            "events_published": 0,
            "events_delivered": 0,
            "handler_errors": 0,
        }

        # Subscription counter for generating unique IDs
        self._subscription_counter = 0

    def subscribe(
        self,
        event_type: Type[Event],
        handler: EventHandler,
    ) -> str:
        """
        Subscribe to events of a specific type.

        Args:
            event_type: The type of event to subscribe to
            handler: Callable that will be invoked when events are published

        Returns:
            Subscription ID for later unsubscription

        Example:
            ```python
            def my_handler(event: NewCandleEvent):
                print(event.symbol)

            sub_id = event_bus.subscribe(NewCandleEvent, my_handler)
            ```
        """
        self._subscription_counter += 1
        subscription_id = f"sub_{self._subscription_counter}_{event_type.__name__}"

        self._subscriptions[event_type].append((subscription_id, handler))

        self.logger.debug(
            f"Subscribed: {subscription_id} to {event_type.__name__} "
            f"(total subscribers: {len(self._subscriptions[event_type])})"
        )

        return subscription_id

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe from events.

        Args:
            subscription_id: The subscription ID returned by subscribe()

        Returns:
            True if unsubscribed successfully, False if not found
        """
        for event_type, handlers in self._subscriptions.items():
            for i, (sub_id, handler) in enumerate(handlers):
                if sub_id == subscription_id:
                    handlers.pop(i)
                    self.logger.debug(f"Unsubscribed: {subscription_id}")
                    return True

        self.logger.warning(f"Subscription not found: {subscription_id}")
        return False

    def publish(self, event: Event) -> None:
        """
        Publish an event to all subscribers.

        Events are delivered synchronously to all registered handlers.
        If a handler raises an exception, it's logged and other handlers continue.

        Args:
            event: The event to publish

        Example:
            ```python
            event = NewCandleEvent(symbol="EURUSD", timeframe="1", bar=...)
            event_bus.publish(event)
            ```
        """
        event_type = type(event)

        # Log event if configured
        if self.log_all_events:
            self.logger.debug(f"Publishing: {event_type.__name__} - {event}")

        # Add to history
        self._event_history.append((datetime.now(), event))

        # Update metrics
        self._metrics["events_published"] += 1

        # Get subscribers for this event type
        subscribers = self._subscriptions.get(event_type, [])

        if not subscribers:
            self.logger.debug(f"No subscribers for {event_type.__name__}")
            return

        # Deliver to all subscribers
        for subscription_id, handler in subscribers:
            try:
                handler(event)
                self._metrics["events_delivered"] += 1
            except Exception as e:
                self._metrics["handler_errors"] += 1
                self.logger.error(
                    f"Error in event handler {subscription_id} "
                    f"for {event_type.__name__}: {e}",
                    exc_info=True
                )

    def get_subscribers(self, event_type: Type[Event]) -> List[EventHandler]:
        """
        Get all subscribers for a specific event type.

        Args:
            event_type: The event type

        Returns:
            List of handler functions
        """
        return [handler for _, handler in self._subscriptions.get(event_type, [])]

    def get_subscriber_count(self, event_type: Type[Event]) -> int:
        """
        Get the number of subscribers for an event type.

        Args:
            event_type: The event type

        Returns:
            Number of subscribers
        """
        return len(self._subscriptions.get(event_type, []))

    def clear_history(self) -> None:
        """Clear the event history."""
        self._event_history.clear()
        self.logger.debug("Event history cleared")

    def get_event_history(
        self,
        event_type: Optional[Type[Event]] = None,
        limit: Optional[int] = None,
    ) -> List[Event]:
        """
        Get event history, optionally filtered by event type.

        Args:
            event_type: Optional event type to filter by
            limit: Optional limit on number of events to return

        Returns:
            List of events from history
        """
        events = [event for _, event in self._event_history]

        # Filter by type if specified
        if event_type:
            events = [e for e in events if isinstance(e, event_type)]

        # Apply limit if specified
        if limit:
            events = events[-limit:]

        return events

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get EventBus metrics.

        Returns:
            Dictionary containing metrics:
            - events_published: Total events published
            - events_delivered: Total events delivered to handlers
            - handler_errors: Total handler errors
            - event_history_size: Current size of event history
            - subscription_count: Number of active subscriptions
        """
        return {
            **self._metrics,
            "event_history_size": len(self._event_history),
            "subscription_count": sum(
                len(handlers) for handlers in self._subscriptions.values()
            ),
            "event_types_subscribed": len(self._subscriptions),
        }

    def clear_subscriptions(self) -> None:
        """Clear all subscriptions. Useful for testing."""
        self._subscriptions.clear()
        self.logger.debug("All subscriptions cleared")

    def __repr__(self) -> str:
        """String representation of EventBus."""
        metrics = self.get_metrics()
        return (
            f"EventBus("
            f"subscriptions={metrics['subscription_count']}, "
            f"events_published={metrics['events_published']}, "
            f"history_size={metrics['event_history_size']}"
            f")"
        )
