"""
Mock EventBus for testing services in isolation.

The MockEventBus allows you to verify that services publish the correct events
without actually delivering them to other services.
"""

from typing import Type, List, Dict, Any
from app.events.base import Event, EventHandler


class MockEventBus:
    """
    Mock EventBus for testing.

    Tracks published events and subscriptions without actually delivering events.
    Useful for testing services in isolation.

    Example:
        ```python
        def test_service_publishes_event():
            mock_bus = MockEventBus()
            service = MyService(event_bus=mock_bus, ...)

            service.do_something()

            # Verify event was published
            events = mock_bus.get_published_events(MyEvent)
            assert len(events) == 1
            assert events[0].symbol == "EURUSD"
        ```
    """

    def __init__(self):
        """Initialize mock event bus."""
        self._published_events: List[Event] = []
        self._subscriptions: Dict[Type[Event], List[EventHandler]] = {}
        self._subscription_counter = 0

    def subscribe(self, event_type: Type[Event], handler: EventHandler) -> str:
        """
        Subscribe to an event type.

        Args:
            event_type: Event type to subscribe to
            handler: Handler function

        Returns:
            Subscription ID
        """
        if event_type not in self._subscriptions:
            self._subscriptions[event_type] = []

        self._subscriptions[event_type].append(handler)
        self._subscription_counter += 1

        return f"mock_sub_{self._subscription_counter}"

    def unsubscribe(self, subscription_id: str) -> bool:
        """
        Unsubscribe (mock implementation).

        Args:
            subscription_id: Subscription ID

        Returns:
            Always True
        """
        return True

    def publish(self, event: Event) -> None:
        """
        Record that an event was published.

        Args:
            event: Event to publish
        """
        self._published_events.append(event)

    def get_published_events(
        self,
        event_type: Type[Event] = None
    ) -> List[Event]:
        """
        Get list of published events, optionally filtered by type.

        Args:
            event_type: Optional event type to filter by

        Returns:
            List of published events
        """
        if event_type is None:
            return self._published_events.copy()

        return [
            event for event in self._published_events
            if isinstance(event, event_type)
        ]

    def get_published_event_types(self) -> List[Type[Event]]:
        """
        Get list of event types that were published.

        Returns:
            List of event types
        """
        return list(set(type(event) for event in self._published_events))

    def clear_published_events(self) -> None:
        """Clear the list of published events."""
        self._published_events.clear()

    def get_event_count(self, event_type: Type[Event] = None) -> int:
        """
        Get count of published events.

        Args:
            event_type: Optional event type to filter by

        Returns:
            Count of published events
        """
        return len(self.get_published_events(event_type))

    def was_event_published(self, event_type: Type[Event]) -> bool:
        """
        Check if any event of given type was published.

        Args:
            event_type: Event type to check

        Returns:
            True if at least one event of this type was published
        """
        return any(isinstance(event, event_type) for event in self._published_events)

    def get_last_published_event(
        self,
        event_type: Type[Event] = None
    ) -> Event:
        """
        Get the last published event, optionally filtered by type.

        Args:
            event_type: Optional event type to filter by

        Returns:
            Last published event, or None if no events
        """
        events = self.get_published_events(event_type)
        return events[-1] if events else None

    def get_subscribers(self, event_type: Type[Event]) -> List[EventHandler]:
        """
        Get subscribers for an event type.

        Args:
            event_type: Event type

        Returns:
            List of handler functions
        """
        return self._subscriptions.get(event_type, []).copy()

    def get_subscriber_count(self, event_type: Type[Event]) -> int:
        """
        Get count of subscribers for an event type.

        Args:
            event_type: Event type

        Returns:
            Number of subscribers
        """
        return len(self._subscriptions.get(event_type, []))
