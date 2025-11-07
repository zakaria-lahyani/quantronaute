"""
Base event classes for the event-driven architecture.

All events inherit from Event and are immutable (frozen dataclasses).
Events include metadata for tracking and debugging.
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol, TypeVar, Optional


@dataclass(frozen=True, kw_only=True)
class Event:
    """
    Base class for all events in the system.

    All events are immutable and include tracking metadata.
    All fields are keyword-only to avoid dataclass ordering issues.

    Attributes:
        event_id: Unique identifier for this event instance
        timestamp: When the event was created
        correlation_id: Correlation ID for tracing event flow (optional)
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = field(default=None)

    def __repr__(self) -> str:
        """Human-readable representation of the event."""
        class_name = self.__class__.__name__
        attrs = ", ".join(
            f"{k}={v!r}"
            for k, v in self.__dict__.items()
            if k not in ["event_id", "timestamp", "correlation_id"]
        )
        return f"{class_name}({attrs})"

    def to_dict(self) -> dict:
        """
        Convert event to dictionary for logging/serialization.

        Returns:
            Dictionary representation of the event
        """
        result = {
            "event_type": self.__class__.__name__,
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
        }

        # Add correlation_id if present
        if self.correlation_id:
            result["correlation_id"] = self.correlation_id

        # Add all other fields
        for k, v in self.__dict__.items():
            if k not in ["event_id", "timestamp", "correlation_id"]:
                # Handle complex types
                if hasattr(v, 'to_dict'):
                    result[k] = v.to_dict()
                elif isinstance(v, (str, int, float, bool, type(None))):
                    result[k] = v
                else:
                    result[k] = str(v)
        return result


# Type variable for events
TEvent = TypeVar("TEvent", bound=Event)


class EventHandler(Protocol[TEvent]):
    """
    Protocol for event handlers.

    Any callable that accepts an event can be an event handler.
    """

    def __call__(self, event: TEvent) -> None:
        """
        Handle the event.

        Args:
            event: The event to handle
        """
        ...
