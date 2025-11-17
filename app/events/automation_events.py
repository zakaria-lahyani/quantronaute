"""
Automation-related events for controlling automated trading.

These events enable runtime control of automated trading behavior through
the event-driven architecture.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional

from app.events.base import Event


class AutomationAction(str, Enum):
    """Actions that can be requested for automation control."""
    ENABLE = "ENABLE"
    DISABLE = "DISABLE"
    QUERY = "QUERY"


@dataclass(frozen=True, kw_only=True)
class ToggleAutomationEvent(Event):
    """
    Event requesting a change to automation state.

    This event is published when an external source (file watcher, API, etc.)
    requests that automated trading be enabled or disabled.

    Attributes:
        action: The automation action to perform (ENABLE, DISABLE, QUERY)
        reason: Human-readable reason for the change
        requested_by: Who/what requested the change (e.g., "file_watcher", "api_user_123")
    """
    action: AutomationAction
    reason: str
    requested_by: str = "system"


@dataclass(frozen=True, kw_only=True)
class AutomationStateChangedEvent(Event):
    """
    Event published when automation state actually changes.

    This event is published by AutomationStateManager after successfully
    updating the automation state. Services subscribe to this event to
    adjust their behavior.

    Attributes:
        enabled: Whether automated trading is now enabled
        previous_state: Previous automation state (None if first initialization)
        reason: Reason for the state change
        changed_at: Timestamp when the change occurred
    """
    enabled: bool
    previous_state: Optional[bool] = None
    reason: str = "system_initialization"
    changed_at: datetime = None

    def __post_init__(self):
        """Set changed_at to current time if not provided."""
        if self.changed_at is None:
            # Use object.__setattr__ because dataclass is frozen
            object.__setattr__(self, 'changed_at', datetime.now())
