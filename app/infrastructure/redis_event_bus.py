"""
Redis-based EventBus for distributed event communication.

This module provides a Redis-backed EventBus that allows multiple containers
(API, multiple broker trading systems) to share events through a central message broker.
"""

import json
import logging
import pickle
import threading
from typing import Any, Callable, Dict, List, Optional, Type
import redis

from app.events.base import Event


class RedisEventBus:
    """
    Redis-based EventBus for cross-container event distribution.

    Uses Redis pub/sub for real-time event distribution across multiple containers.
    All events are serialized and published to Redis channels based on event type.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        logger: Optional[logging.Logger] = None,
        log_all_events: bool = False
    ):
        """
        Initialize Redis EventBus.

        Args:
            redis_url: Redis connection URL (e.g., "redis://localhost:6379/0")
            logger: Optional logger instance
            log_all_events: Whether to log all published events
        """
        self.logger = logger or logging.getLogger(__name__)
        self.log_all_events = log_all_events

        # Connect to Redis
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=False)
            self.pubsub = self.redis_client.pubsub()
            self.logger.info(f"✓ Connected to Redis at {redis_url}")
        except Exception as e:
            self.logger.error(f"✗ Failed to connect to Redis: {e}")
            raise

        # Subscriber thread
        self._subscriber_thread: Optional[threading.Thread] = None
        self._running = False

        # Event handlers: {event_type_name: [handler1, handler2, ...]}
        self._handlers: Dict[str, List[Callable]] = {}

        # Metrics
        self._events_published = 0
        self._events_received = 0
        self._handler_errors = 0

    def start(self):
        """Start the Redis subscriber thread."""
        if self._running:
            self.logger.warning("RedisEventBus already running")
            return

        self._running = True
        self._subscriber_thread = threading.Thread(target=self._run_subscriber, daemon=True)
        self._subscriber_thread.start()
        self.logger.info("RedisEventBus subscriber started")

    def stop(self):
        """Stop the Redis subscriber thread."""
        if not self._running:
            return

        self._running = False
        self.pubsub.close()

        if self._subscriber_thread:
            self._subscriber_thread.join(timeout=5)

        self.redis_client.close()
        self.logger.info("RedisEventBus stopped")

    def subscribe(self, event_type: Type[Event], handler: Callable[[Event], None]) -> str:
        """
        Subscribe to an event type.

        Args:
            event_type: The event class to subscribe to
            handler: Callback function to handle the event

        Returns:
            Subscription ID (for potential unsubscribe)
        """
        event_type_name = event_type.__name__

        if event_type_name not in self._handlers:
            self._handlers[event_type_name] = []
            # Subscribe to Redis channel for this event type
            self.pubsub.subscribe(f"events:{event_type_name}")
            self.logger.debug(f"Subscribed to Redis channel: events:{event_type_name}")

        self._handlers[event_type_name].append(handler)

        subscription_id = f"{event_type_name}:{id(handler)}"
        self.logger.debug(f"Handler registered: {subscription_id}")

        return subscription_id

    def unsubscribe(self, subscription_id: str):
        """
        Unsubscribe a handler.

        Args:
            subscription_id: ID returned by subscribe()
        """
        # Parse subscription_id
        event_type_name, handler_id = subscription_id.split(":", 1)

        if event_type_name in self._handlers:
            # Find and remove handler by ID
            self._handlers[event_type_name] = [
                h for h in self._handlers[event_type_name]
                if str(id(h)) != handler_id
            ]

            # If no more handlers, unsubscribe from Redis
            if not self._handlers[event_type_name]:
                del self._handlers[event_type_name]
                self.pubsub.unsubscribe(f"events:{event_type_name}")
                self.logger.debug(f"Unsubscribed from Redis channel: events:{event_type_name}")

    def publish(self, event: Event):
        """
        Publish an event to Redis.

        Args:
            event: Event instance to publish
        """
        event_type_name = type(event).__name__
        channel = f"events:{event_type_name}"

        try:
            # Serialize event using pickle (preserves full object)
            serialized_event = pickle.dumps(event)

            # Publish to Redis
            self.redis_client.publish(channel, serialized_event)
            self._events_published += 1

            if self.log_all_events:
                self.logger.debug(f"📤 Published to Redis: {event_type_name}")

        except Exception as e:
            self.logger.error(f"Failed to publish event {event_type_name}: {e}")

    def _run_subscriber(self):
        """Run the Redis subscriber loop (runs in separate thread)."""
        self.logger.info("Redis subscriber thread started")

        try:
            for message in self.pubsub.listen():
                if not self._running:
                    break

                if message['type'] != 'message':
                    continue

                try:
                    # Deserialize event
                    event = pickle.loads(message['data'])
                    event_type_name = type(event).__name__

                    self._events_received += 1

                    if self.log_all_events:
                        self.logger.debug(f"📥 Received from Redis: {event_type_name}")

                    # Dispatch to handlers
                    handlers = self._handlers.get(event_type_name, [])
                    for handler in handlers:
                        try:
                            handler(event)
                        except Exception as e:
                            self._handler_errors += 1
                            self.logger.error(
                                f"Error in handler for {event_type_name}: {e}",
                                exc_info=True
                            )

                except Exception as e:
                    self.logger.error(f"Error processing Redis message: {e}")

        except Exception as e:
            if self._running:  # Only log if this wasn't an intentional stop
                self.logger.error(f"Redis subscriber error: {e}")

        self.logger.info("Redis subscriber thread stopped")

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get EventBus metrics.

        Returns:
            Dictionary containing metrics
        """
        return {
            "events_published": self._events_published,
            "events_received": self._events_received,
            "handler_errors": self._handler_errors,
            "active_subscriptions": len(self._handlers),
            "event_types": list(self._handlers.keys())
        }

    def get_event_history(self, event_type: Optional[Type] = None, limit: int = 100) -> List[Any]:
        """
        Get recent event history.

        Note: Redis pub/sub doesn't store history by default.
        This method returns empty list. For history, use Redis Streams instead.

        Args:
            event_type: Optional event type to filter
            limit: Maximum number of events

        Returns:
            Empty list (history not supported in pub/sub mode)
        """
        self.logger.warning("Event history not supported with Redis pub/sub")
        return []
