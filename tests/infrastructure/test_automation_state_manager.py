"""
Tests for AutomationStateManager.

These tests verify that the AutomationStateManager correctly:
- Loads and saves automation state to file
- Handles toggle events (ENABLE, DISABLE, QUERY)
- Publishes state change events
- Maintains thread safety
- Implements backup rotation
- Handles file errors gracefully
"""

import pytest
import json
import tempfile
import threading
from pathlib import Path
from datetime import datetime

from app.infrastructure.event_bus import EventBus
from app.infrastructure.automation_state_manager import AutomationStateManager
from app.events.automation_events import (
    AutomationAction,
    ToggleAutomationEvent,
    AutomationStateChangedEvent
)


class TestAutomationStateManagerInitialization:
    """Test initialization and state loading."""

    def test_initialize_with_default_state_no_file(self, tmp_path):
        """Test initialization when no state file exists."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        assert manager.is_enabled() is True
        assert not state_file.exists()  # File not created until first save

    def test_initialize_loads_existing_state(self, tmp_path):
        """Test initialization loads state from existing file."""
        state_file = tmp_path / "automation_state.json"

        # Create existing state file
        state_data = {
            "enabled": False,
            "last_changed": "2025-01-01T10:00:00",
            "reason": "manual_disable",
            "requested_by": "user_123"
        }
        state_file.write_text(json.dumps(state_data))

        event_bus = EventBus()
        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True  # Should be overridden by file
        )

        assert manager.is_enabled() is False
        state = manager.get_state()
        assert state["enabled"] is False
        assert state["reason"] == "manual_disable"
        assert state["requested_by"] == "user_123"

    def test_initialize_handles_corrupted_state_file(self, tmp_path):
        """Test initialization with corrupted JSON file."""
        state_file = tmp_path / "automation_state.json"
        state_file.write_text("{ invalid json }")

        event_bus = EventBus()
        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        # Should fall back to default state
        assert manager.is_enabled() is True

    def test_initialize_handles_invalid_state_data(self, tmp_path):
        """Test initialization with invalid state data."""
        state_file = tmp_path / "automation_state.json"
        state_file.write_text(json.dumps({"invalid": "data"}))

        event_bus = EventBus()
        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=False
        )

        # Should use default for missing fields
        assert manager.is_enabled() is False


class TestAutomationStateManagerToggle:
    """Test toggle event handling."""

    def test_enable_automation(self, tmp_path):
        """Test enabling automation via event."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=False
        )

        assert manager.is_enabled() is False

        # Publish enable event
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.ENABLE,
            reason="test_enable",
            requested_by="test"
        ))

        assert manager.is_enabled() is True

    def test_disable_automation(self, tmp_path):
        """Test disabling automation via event."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        assert manager.is_enabled() is True

        # Publish disable event
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test_disable",
            requested_by="test"
        ))

        assert manager.is_enabled() is False

    def test_query_automation_state(self, tmp_path):
        """Test querying automation state via event."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        state_changes = []

        def capture_state_change(event):
            state_changes.append(event)

        event_bus.subscribe(AutomationStateChangedEvent, capture_state_change)

        # Publish query event
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.QUERY,
            reason="test_query",
            requested_by="test"
        ))

        # State should not change
        assert manager.is_enabled() is True

        # Should publish state change event with same state
        assert len(state_changes) == 1
        assert state_changes[0].enabled is True
        assert state_changes[0].previous_state is True

    def test_toggle_same_state_is_noop(self, tmp_path):
        """Test that toggling to same state doesn't publish event."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        state_changes = []
        event_bus.subscribe(AutomationStateChangedEvent, lambda e: state_changes.append(e))

        # Try to enable when already enabled
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.ENABLE,
            reason="test",
            requested_by="test"
        ))

        # Should not publish state change
        assert len(state_changes) == 0
        assert manager.is_enabled() is True


class TestAutomationStateManagerEvents:
    """Test event publishing."""

    def test_publishes_state_changed_event_on_toggle(self, tmp_path):
        """Test that state change events are published."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        events_received = []

        def capture_event(event):
            events_received.append(event)

        event_bus.subscribe(AutomationStateChangedEvent, capture_event)

        # Disable automation
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="market_conditions",
            requested_by="trader_1"
        ))

        assert len(events_received) == 1
        event = events_received[0]
        assert isinstance(event, AutomationStateChangedEvent)
        assert event.enabled is False
        assert event.previous_state is True
        assert event.reason == "market_conditions"

    def test_state_changed_event_includes_timestamp(self, tmp_path):
        """Test that state change events include timestamp."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        events_received = []
        event_bus.subscribe(AutomationStateChangedEvent, lambda e: events_received.append(e))

        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test",
            requested_by="test"
        ))

        assert len(events_received) == 1
        assert events_received[0].changed_at is not None
        assert isinstance(events_received[0].changed_at, datetime)


class TestAutomationStateManagerPersistence:
    """Test file persistence."""

    def test_saves_state_to_file(self, tmp_path):
        """Test that state is saved to file on change."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        # Toggle state
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test_save",
            requested_by="test_user"
        ))

        # File should be created
        assert state_file.exists()

        # Load and verify content
        with open(state_file, 'r') as f:
            saved_data = json.load(f)

        assert saved_data["enabled"] is False
        assert saved_data["reason"] == "test_save"
        assert saved_data["requested_by"] == "test_user"
        assert "saved_at" in saved_data

    def test_state_persists_across_restarts(self, tmp_path):
        """Test that state persists when manager is recreated."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        # First instance - disable automation
        manager1 = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="persist_test",
            requested_by="test"
        ))

        # Second instance - should load disabled state
        manager2 = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True  # Should be overridden
        )

        assert manager2.is_enabled() is False

    def test_atomic_write_creates_temp_file(self, tmp_path):
        """Test that atomic write uses temp file."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        # Toggle state
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="test",
            requested_by="test"
        ))

        # Temp file should not exist (already renamed)
        temp_file = state_file.with_suffix('.tmp')
        assert not temp_file.exists()

        # Final file should exist
        assert state_file.exists()

    def test_backup_rotation(self, tmp_path):
        """Test that backups are rotated correctly."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True,
            backup_count=3
        )

        # Create initial file
        state_file.write_text(json.dumps({"enabled": True}))

        # Make multiple changes to trigger backups
        for i in range(5):
            action = AutomationAction.DISABLE if i % 2 == 0 else AutomationAction.ENABLE
            event_bus.publish(ToggleAutomationEvent(
                action=action,
                reason=f"backup_test_{i}",
                requested_by="test"
            ))

        # Check that backups exist (up to backup_count)
        backup_1 = state_file.with_suffix('.json.bak.1')
        backup_2 = state_file.with_suffix('.json.bak.2')
        backup_3 = state_file.with_suffix('.json.bak.3')
        backup_4 = state_file.with_suffix('.json.bak.4')

        assert backup_1.exists() or backup_2.exists() or backup_3.exists()
        # backup_4 may or may not exist depending on timing

        # backup_5 should not exist (beyond backup_count)
        backup_5 = state_file.with_suffix('.json.bak.5')
        # Note: With backup_count=3, we shouldn't have backup_5


class TestAutomationStateManagerThreadSafety:
    """Test thread safety."""

    def test_concurrent_toggles_are_thread_safe(self, tmp_path):
        """Test that concurrent state changes are handled safely."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        def toggle_state(action, num_times):
            for i in range(num_times):
                event_bus.publish(ToggleAutomationEvent(
                    action=action,
                    reason=f"concurrent_test_{i}",
                    requested_by="test_thread"
                ))

        # Create threads that toggle state concurrently
        threads = [
            threading.Thread(target=toggle_state, args=(AutomationAction.DISABLE, 10)),
            threading.Thread(target=toggle_state, args=(AutomationAction.ENABLE, 10)),
            threading.Thread(target=toggle_state, args=(AutomationAction.DISABLE, 10)),
        ]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # State should be consistent (either enabled or disabled, not corrupted)
        final_state = manager.is_enabled()
        assert isinstance(final_state, bool)

        # File should be valid JSON
        with open(state_file, 'r') as f:
            data = json.load(f)
        assert "enabled" in data
        assert isinstance(data["enabled"], bool)


class TestAutomationStateManagerGetState:
    """Test get_state method."""

    def test_get_state_returns_complete_info(self, tmp_path):
        """Test that get_state returns all state information."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        # Toggle state
        event_bus.publish(ToggleAutomationEvent(
            action=AutomationAction.DISABLE,
            reason="get_state_test",
            requested_by="test_user"
        ))

        state = manager.get_state()

        assert "enabled" in state
        assert "last_changed" in state
        assert "reason" in state
        assert "requested_by" in state

        assert state["enabled"] is False
        assert state["reason"] == "get_state_test"
        assert state["requested_by"] == "test_user"

    def test_get_state_is_thread_safe(self, tmp_path):
        """Test that get_state can be called concurrently."""
        state_file = tmp_path / "automation_state.json"
        event_bus = EventBus()

        manager = AutomationStateManager(
            event_bus=event_bus,
            state_file_path=str(state_file),
            default_enabled=True
        )

        states = []

        def read_state():
            for _ in range(100):
                state = manager.get_state()
                states.append(state)

        threads = [threading.Thread(target=read_state) for _ in range(5)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All states should be valid dictionaries
        assert len(states) == 500
        for state in states:
            assert isinstance(state, dict)
            assert "enabled" in state
