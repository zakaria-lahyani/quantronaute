"""
Tests for EventBus implementation.

These tests verify that the EventBus correctly:
- Subscribes and unsubscribes handlers
- Publishes events to subscribers
- Handles errors in handlers
- Tracks metrics and history
"""

import pytest
from app.infrastructure.event_bus import EventBus
from app.events.data_events import NewCandleEvent, DataFetchedEvent
from app.events.strategy_events import EntrySignalEvent
from tests.fixtures.events import create_new_candle_event, create_entry_signal_event


class TestEventBusSubscription:
    """Test event subscription functionality."""

    def test_subscribe_returns_subscription_id(self):
        """Test that subscribe returns a unique subscription ID."""
        event_bus = EventBus()

        def handler(event): pass

        sub_id = event_bus.subscribe(NewCandleEvent, handler)

        assert sub_id is not None
        assert isinstance(sub_id, str)
        assert "sub_" in sub_id
        assert "NewCandleEvent" in sub_id

    def test_subscribe_multiple_handlers(self):
        """Test subscribing multiple handlers to same event type."""
        event_bus = EventBus()

        def handler1(event): pass
        def handler2(event): pass

        sub_id1 = event_bus.subscribe(NewCandleEvent, handler1)
        sub_id2 = event_bus.subscribe(NewCandleEvent, handler2)

        assert sub_id1 != sub_id2
        assert event_bus.get_subscriber_count(NewCandleEvent) == 2

    def test_unsubscribe_removes_handler(self):
        """Test that unsubscribe removes the handler."""
        event_bus = EventBus()

        def handler(event): pass

        sub_id = event_bus.subscribe(NewCandleEvent, handler)
        assert event_bus.get_subscriber_count(NewCandleEvent) == 1

        result = event_bus.unsubscribe(sub_id)

        assert result is True
        assert event_bus.get_subscriber_count(NewCandleEvent) == 0

    def test_unsubscribe_nonexistent_returns_false(self):
        """Test unsubscribing with invalid ID returns False."""
        event_bus = EventBus()

        result = event_bus.unsubscribe("invalid_id")

        assert result is False


class TestEventBusPublishing:
    """Test event publishing functionality."""

    def test_publish_delivers_to_subscriber(self):
        """Test that published events are delivered to subscribers."""
        event_bus = EventBus()
        received_events = []

        def handler(event):
            received_events.append(event)

        event_bus.subscribe(NewCandleEvent, handler)

        event = create_new_candle_event()
        event_bus.publish(event)

        assert len(received_events) == 1
        assert received_events[0] == event

    def test_publish_delivers_to_multiple_subscribers(self):
        """Test event delivered to all subscribers."""
        event_bus = EventBus()
        received_events_1 = []
        received_events_2 = []

        def handler1(event):
            received_events_1.append(event)

        def handler2(event):
            received_events_2.append(event)

        event_bus.subscribe(NewCandleEvent, handler1)
        event_bus.subscribe(NewCandleEvent, handler2)

        event = create_new_candle_event()
        event_bus.publish(event)

        assert len(received_events_1) == 1
        assert len(received_events_2) == 1
        assert received_events_1[0] == event
        assert received_events_2[0] == event

    def test_publish_only_to_matching_event_type(self):
        """Test events only delivered to matching event type subscribers."""
        event_bus = EventBus()
        candle_events = []
        signal_events = []

        def candle_handler(event):
            candle_events.append(event)

        def signal_handler(event):
            signal_events.append(event)

        event_bus.subscribe(NewCandleEvent, candle_handler)
        event_bus.subscribe(EntrySignalEvent, signal_handler)

        # Publish candle event
        candle_event = create_new_candle_event()
        event_bus.publish(candle_event)

        assert len(candle_events) == 1
        assert len(signal_events) == 0

        # Publish signal event
        signal_event = create_entry_signal_event()
        event_bus.publish(signal_event)

        assert len(candle_events) == 1
        assert len(signal_events) == 1

    def test_publish_with_no_subscribers(self):
        """Test publishing when no one is subscribed doesn't error."""
        event_bus = EventBus()

        event = create_new_candle_event()
        # Should not raise an exception
        event_bus.publish(event)


class TestEventBusErrorHandling:
    """Test error handling in event bus."""

    def test_handler_error_doesnt_affect_other_handlers(self):
        """Test that one handler's error doesn't prevent others from receiving events."""
        event_bus = EventBus()
        received_events = []

        def failing_handler(event):
            raise ValueError("Handler error")

        def working_handler(event):
            received_events.append(event)

        event_bus.subscribe(NewCandleEvent, failing_handler)
        event_bus.subscribe(NewCandleEvent, working_handler)

        event = create_new_candle_event()
        event_bus.publish(event)

        # Working handler should still receive the event
        assert len(received_events) == 1
        assert received_events[0] == event

        # Metrics should track the error
        metrics = event_bus.get_metrics()
        assert metrics["handler_errors"] == 1


class TestEventBusHistory:
    """Test event history functionality."""

    def test_event_history_stores_published_events(self):
        """Test that published events are stored in history."""
        event_bus = EventBus(event_history_limit=10)

        event1 = create_new_candle_event(symbol="EURUSD")
        event2 = create_new_candle_event(symbol="GBPUSD")

        event_bus.publish(event1)
        event_bus.publish(event2)

        history = event_bus.get_event_history()

        assert len(history) == 2
        assert history[0] == event1
        assert history[1] == event2

    def test_event_history_filters_by_type(self):
        """Test filtering event history by event type."""
        event_bus = EventBus()

        candle_event = create_new_candle_event()
        signal_event = create_entry_signal_event()

        event_bus.publish(candle_event)
        event_bus.publish(signal_event)

        candle_history = event_bus.get_event_history(NewCandleEvent)
        signal_history = event_bus.get_event_history(EntrySignalEvent)

        assert len(candle_history) == 1
        assert len(signal_history) == 1
        assert candle_history[0] == candle_event
        assert signal_history[0] == signal_event

    def test_event_history_respects_limit(self):
        """Test that event history is limited to configured size."""
        event_bus = EventBus(event_history_limit=3)

        # Publish 5 events
        for i in range(5):
            event_bus.publish(create_new_candle_event())

        history = event_bus.get_event_history()

        # Should only keep last 3
        assert len(history) == 3

    def test_clear_history(self):
        """Test clearing event history."""
        event_bus = EventBus()

        event_bus.publish(create_new_candle_event())
        assert len(event_bus.get_event_history()) == 1

        event_bus.clear_history()
        assert len(event_bus.get_event_history()) == 0


class TestEventBusMetrics:
    """Test metrics tracking."""

    def test_metrics_track_published_events(self):
        """Test that metrics track published events."""
        event_bus = EventBus()

        event_bus.publish(create_new_candle_event())
        event_bus.publish(create_new_candle_event())

        metrics = event_bus.get_metrics()

        assert metrics["events_published"] == 2

    def test_metrics_track_delivered_events(self):
        """Test that metrics track delivered events."""
        event_bus = EventBus()

        def handler(event): pass

        event_bus.subscribe(NewCandleEvent, handler)

        event_bus.publish(create_new_candle_event())
        event_bus.publish(create_new_candle_event())

        metrics = event_bus.get_metrics()

        assert metrics["events_delivered"] == 2

    def test_metrics_track_subscriptions(self):
        """Test that metrics track subscription count."""
        event_bus = EventBus()

        def handler(event): pass

        event_bus.subscribe(NewCandleEvent, handler)
        event_bus.subscribe(EntrySignalEvent, handler)

        metrics = event_bus.get_metrics()

        assert metrics["subscription_count"] == 2
        assert metrics["event_types_subscribed"] == 2
