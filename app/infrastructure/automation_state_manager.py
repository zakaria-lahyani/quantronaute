"""
Automation State Manager for controlling automated trading at runtime.

This module provides the core state management for automated trading control,
with file persistence and event-driven state changes.
"""

import json
import logging
import os
import shutil
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from app.events.automation_events import (
    AutomationAction,
    ToggleAutomationEvent,
    AutomationStateChangedEvent,
)
from app.infrastructure.event_bus import EventBus


class AutomationStateManager:
    """
    Manages automated trading state with file persistence and event publishing.

    The AutomationStateManager:
    - Subscribes to ToggleAutomationEvent to receive state change requests
    - Maintains automation state (enabled/disabled) in memory
    - Persists state to JSON file for persistence across restarts
    - Publishes AutomationStateChangedEvent when state changes
    - Provides thread-safe state updates
    - Implements atomic file writes with backup rotation

    Example:
        ```python
        event_bus = EventBus()
        state_manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path="config/automation_state.json",
            default_enabled=True
        )

        # State changes are triggered by publishing events
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="Market volatility",
            requested_by="user_123"
        ))
        ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        state_file_path: str = "config/automation_state.json",
        default_enabled: bool = True,
        backup_count: int = 5,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize the AutomationStateManager.

        Args:
            event_bus: EventBus instance for subscribing/publishing events
            state_file_path: Path to JSON file for state persistence
            default_enabled: Default state if no file exists (default: True)
            backup_count: Number of backup files to keep (default: 5)
            logger: Optional logger instance
        """
        self.event_bus = event_bus
        self.state_file_path = Path(state_file_path)
        self.default_enabled = default_enabled
        self.backup_count = backup_count
        self.logger = logger or logging.getLogger(__name__)

        # Thread safety lock
        self._lock = threading.Lock()

        # Current automation state
        self._enabled: bool = default_enabled
        self._last_changed: Optional[datetime] = None
        self._last_reason: str = "system_initialization"
        self._last_requested_by: str = "system"

        # Load state from file
        self._load_state()

        # Subscribe to toggle events
        self.event_bus.subscribe(ToggleAutomationEvent, self._handle_toggle_event)

        self.logger.info(
            f"AutomationStateManager initialized - automation {'enabled' if self._enabled else 'disabled'}"
        )

    def _load_state(self) -> None:
        """
        Load automation state from JSON file.

        If the file doesn't exist, use the default state.
        If the file is corrupted, log error and use default state.
        """
        if not self.state_file_path.exists():
            self.logger.info(
                f"State file not found: {self.state_file_path}, using default state (enabled={self.default_enabled})"
            )
            return

        try:
            with open(self.state_file_path, 'r') as f:
                state_data = json.load(f)

            self._enabled = state_data.get("enabled", self.default_enabled)
            self._last_reason = state_data.get("reason", "loaded_from_file")
            self._last_requested_by = state_data.get("requested_by", "system")

            # Parse last_changed timestamp
            if last_changed_str := state_data.get("last_changed"):
                try:
                    self._last_changed = datetime.fromisoformat(last_changed_str)
                except ValueError:
                    self.logger.warning(f"Invalid timestamp in state file: {last_changed_str}")
                    self._last_changed = datetime.now()
            else:
                self._last_changed = datetime.now()

            self.logger.info(
                f"Loaded automation state from file: enabled={self._enabled}, "
                f"last_changed={self._last_changed}, reason='{self._last_reason}'"
            )

        except json.JSONDecodeError as e:
            self.logger.error(
                f"Failed to parse state file {self.state_file_path}: {e}. "
                f"Using default state (enabled={self.default_enabled})"
            )
        except Exception as e:
            self.logger.error(
                f"Unexpected error loading state file {self.state_file_path}: {e}. "
                f"Using default state (enabled={self.default_enabled})"
            )

    def _save_state(self) -> None:
        """
        Save automation state to JSON file with atomic write.

        Uses atomic write pattern:
        1. Write to temporary file
        2. Rename temporary file to target file (atomic operation)
        3. Create backup of previous version
        4. Rotate old backups

        Raises:
            IOError: If file write fails after retries
        """
        state_data = {
            "enabled": self._enabled,
            "last_changed": self._last_changed.isoformat() if self._last_changed else None,
            "reason": self._last_reason,
            "requested_by": self._last_requested_by,
            "saved_at": datetime.now().isoformat(),
        }

        # Ensure parent directory exists
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write to temporary file first (atomic write pattern)
        temp_file = self.state_file_path.with_suffix('.tmp')

        try:
            with open(temp_file, 'w') as f:
                json.dump(state_data, f, indent=2)

            # Create backup if current file exists
            if self.state_file_path.exists():
                self._rotate_backups()
                backup_file = self.state_file_path.with_suffix('.json.bak.1')
                shutil.copy2(self.state_file_path, backup_file)

            # Atomic rename
            temp_file.replace(self.state_file_path)

            self.logger.info(f"Saved automation state to {self.state_file_path}")

        except Exception as e:
            self.logger.error(f"Failed to save state to {self.state_file_path}: {e}")
            # Clean up temp file if it exists
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except:
                    pass
            raise IOError(f"Failed to save automation state: {e}") from e

    def _rotate_backups(self) -> None:
        """
        Rotate backup files, keeping only the configured number of backups.

        Rotates: file.bak.5 -> deleted, file.bak.4 -> file.bak.5, etc.
        """
        try:
            # Remove oldest backup if it exists
            oldest_backup = self.state_file_path.with_suffix(f'.json.bak.{self.backup_count}')
            if oldest_backup.exists():
                oldest_backup.unlink()

            # Rotate existing backups
            for i in range(self.backup_count - 1, 0, -1):
                current_backup = self.state_file_path.with_suffix(f'.json.bak.{i}')
                next_backup = self.state_file_path.with_suffix(f'.json.bak.{i + 1}')

                if current_backup.exists():
                    current_backup.rename(next_backup)

        except Exception as e:
            self.logger.warning(f"Failed to rotate backups: {e}")

    def _handle_toggle_event(self, event: ToggleAutomationEvent) -> None:
        """
        Handle ToggleAutomationEvent to change automation state.

        Args:
            event: ToggleAutomationEvent with action, reason, requested_by
        """
        with self._lock:
            if event.action == AutomationAction.QUERY:
                # Query doesn't change state, just publish current state
                self.logger.info(f"Automation state query: enabled={self._enabled}")
                self._publish_state_change(previous_state=self._enabled)
                return

            # Determine new state
            new_enabled = (event.action == AutomationAction.ENABLE)

            # Check if state actually changed
            if new_enabled == self._enabled:
                self.logger.info(
                    f"Automation already {'enabled' if new_enabled else 'disabled'}, no change needed"
                )
                return

            # Store previous state
            previous_state = self._enabled

            # Update state
            self._enabled = new_enabled
            self._last_changed = datetime.now()
            self._last_reason = event.reason
            self._last_requested_by = event.requested_by

            # Log state change
            self.logger.info(
                f"Automation {'enabled' if new_enabled else 'disabled'} - "
                f"reason: '{event.reason}', requested_by: '{event.requested_by}'"
            )

            # Persist to file
            try:
                self._save_state()
            except Exception as e:
                self.logger.error(f"Failed to persist state change: {e}")
                # Continue anyway - state is updated in memory

            # Publish state change event
            self._publish_state_change(previous_state=previous_state)

    def _publish_state_change(self, previous_state: Optional[bool] = None) -> None:
        """
        Publish AutomationStateChangedEvent to notify services.

        Args:
            previous_state: Previous automation state (None if first initialization)
        """
        event = AutomationStateChangedEvent(
            enabled=self._enabled,
            previous_state=previous_state,
            reason=self._last_reason,
            changed_at=self._last_changed or datetime.now(),
        )

        self.event_bus.publish(event)

        self.logger.debug(
            f"Published AutomationStateChangedEvent: enabled={self._enabled}, "
            f"previous_state={previous_state}"
        )

    def is_enabled(self) -> bool:
        """
        Check if automated trading is currently enabled.

        Returns:
            True if automation is enabled, False otherwise
        """
        with self._lock:
            return self._enabled

    def get_state(self) -> Dict[str, Any]:
        """
        Get current automation state details.

        Returns:
            Dictionary with state details:
            - enabled: bool
            - last_changed: datetime
            - reason: str
            - requested_by: str
        """
        with self._lock:
            return {
                "enabled": self._enabled,
                "last_changed": self._last_changed.isoformat() if self._last_changed else None,
                "reason": self._last_reason,
                "requested_by": self._last_requested_by,
            }
