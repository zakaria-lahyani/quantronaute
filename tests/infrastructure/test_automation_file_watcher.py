"""
Tests for AutomationFileWatcher.

These tests verify that the AutomationFileWatcher correctly:
- Polls toggle file for commands
- Parses ENABLE, DISABLE, QUERY commands
- Publishes ToggleAutomationEvent
- Logs actions to automation log
- Handles file errors gracefully
- Implements log rotation
"""

import pytest
import time
from pathlib import Path

from app.infrastructure.event_bus import EventBus
from app.infrastructure.automation_file_watcher import AutomationFileWatcher
from app.events.automation_events import ToggleAutomationEvent, AutomationAction


class TestAutomationFileWatcherInitialization:
    """Test initialization."""

    def test_initialize_creates_watcher(self, tmp_path):
        """Test basic initialization."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        assert watcher is not None
        assert not watcher.is_running()

    def test_start_begins_polling(self, tmp_path):
        """Test that start begins the polling loop."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        assert watcher.is_running()

        watcher.stop()

    def test_stop_ends_polling(self, tmp_path):
        """Test that stop ends the polling loop."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()
        assert watcher.is_running()

        watcher.stop()
        assert not watcher.is_running()

    def test_start_when_already_running_is_noop(self, tmp_path):
        """Test that starting an already running watcher is safe."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()
        watcher.start()  # Should not cause error

        assert watcher.is_running()

        watcher.stop()


class TestAutomationFileWatcherCommandParsing:
    """Test command parsing and event publishing."""

    def test_parses_enable_command(self, tmp_path):
        """Test parsing ENABLE command."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        events_received = []
        event_bus.subscribe(ToggleAutomationEvent, lambda e: events_received.append(e))

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Write ENABLE command
        toggle_file.write_text("ENABLE")

        # Wait for polling
        time.sleep(1.5)

        watcher.stop()

        # Should have received event
        assert len(events_received) == 1
        assert events_received[0].action == AutomationAction.ENABLE

    def test_parses_disable_command(self, tmp_path):
        """Test parsing DISABLE command."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        events_received = []
        event_bus.subscribe(ToggleAutomationEvent, lambda e: events_received.append(e))

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Write DISABLE command
        toggle_file.write_text("DISABLE")

        # Wait for polling
        time.sleep(1.5)

        watcher.stop()

        # Should have received event
        assert len(events_received) == 1
        assert events_received[0].action == AutomationAction.DISABLE

    def test_parses_query_command(self, tmp_path):
        """Test parsing QUERY command."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        events_received = []
        event_bus.subscribe(ToggleAutomationEvent, lambda e: events_received.append(e))

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Write QUERY command
        toggle_file.write_text("QUERY")

        # Wait for polling
        time.sleep(1.5)

        watcher.stop()

        # Should have received event
        assert len(events_received) == 1
        assert events_received[0].action == AutomationAction.QUERY

    def test_parses_case_insensitive(self, tmp_path):
        """Test that commands are case-insensitive."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        events_received = []
        event_bus.subscribe(ToggleAutomationEvent, lambda e: events_received.append(e))

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Write lowercase command
        toggle_file.write_text("enable")

        # Wait for polling
        time.sleep(1.5)

        watcher.stop()

        # Should have received event
        assert len(events_received) == 1
        assert events_received[0].action == AutomationAction.ENABLE

    def test_strips_whitespace(self, tmp_path):
        """Test that whitespace is stripped from commands."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        events_received = []
        event_bus.subscribe(ToggleAutomationEvent, lambda e: events_received.append(e))

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Write command with whitespace
        toggle_file.write_text("  DISABLE  \n")

        # Wait for polling
        time.sleep(1.5)

        watcher.stop()

        # Should have received event
        assert len(events_received) == 1
        assert events_received[0].action == AutomationAction.DISABLE

    def test_ignores_invalid_commands(self, tmp_path):
        """Test that invalid commands are ignored."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        events_received = []
        event_bus.subscribe(ToggleAutomationEvent, lambda e: events_received.append(e))

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Write invalid command
        toggle_file.write_text("INVALID_COMMAND")

        # Wait for polling
        time.sleep(1.5)

        watcher.stop()

        # Should not have received event
        assert len(events_received) == 0

    def test_ignores_empty_file(self, tmp_path):
        """Test that empty toggle file is ignored."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        events_received = []
        event_bus.subscribe(ToggleAutomationEvent, lambda e: events_received.append(e))

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Create empty file
        toggle_file.write_text("")

        # Wait for polling
        time.sleep(1.5)

        watcher.stop()

        # Should not have received event
        assert len(events_received) == 0


class TestAutomationFileWatcherLogging:
    """Test action logging."""

    def test_logs_successful_command(self, tmp_path):
        """Test that successful commands are logged."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Write command
        toggle_file.write_text("ENABLE")

        # Wait for polling
        time.sleep(1.5)

        watcher.stop()

        # Check log file
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "SUCCESS" in log_content
        assert "ENABLE" in log_content

    def test_logs_invalid_command(self, tmp_path):
        """Test that invalid commands are logged."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Write invalid command
        toggle_file.write_text("INVALID")

        # Wait for polling
        time.sleep(1.5)

        watcher.stop()

        # Check log file
        assert log_file.exists()
        log_content = log_file.read_text()
        assert "ERROR" in log_content or "Invalid command" in log_content

    def test_log_format_includes_timestamp(self, tmp_path):
        """Test that log entries include timestamps."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Write command
        toggle_file.write_text("ENABLE")

        # Wait for polling
        time.sleep(1.5)

        watcher.stop()

        # Check log format
        log_content = log_file.read_text()
        # Format should be: YYYY-MM-DD HH:MM:SS - STATUS - Message
        assert "-" in log_content
        # Check year is present
        assert "202" in log_content


class TestAutomationFileWatcherFileHandling:
    """Test file handling behavior."""

    def test_handles_nonexistent_file_gracefully(self, tmp_path):
        """Test that watcher handles non-existent toggle file."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        # Start without creating toggle file
        watcher.start()

        # Wait for polling
        time.sleep(1.5)

        # Should not crash
        assert watcher.is_running()

        watcher.stop()

    def test_avoids_duplicate_processing(self, tmp_path):
        """Test that same command is not processed multiple times."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        events_received = []
        event_bus.subscribe(ToggleAutomationEvent, lambda e: events_received.append(e))

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Write command
        toggle_file.write_text("ENABLE")

        # Wait for multiple polling cycles
        time.sleep(3)

        watcher.stop()

        # Should only process once (not duplicate)
        assert len(events_received) == 1

    def test_processes_new_command_after_file_modification(self, tmp_path):
        """Test that file modification is detected."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        events_received = []
        event_bus.subscribe(ToggleAutomationEvent, lambda e: events_received.append(e))

        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=1
        )

        watcher.start()

        # Write first command
        toggle_file.write_text("ENABLE")
        time.sleep(1.5)

        # Modify file with different command
        time.sleep(0.5)  # Ensure different modification time
        toggle_file.write_text("DISABLE")
        time.sleep(1.5)

        watcher.stop()

        # Should have processed both commands
        assert len(events_received) == 2
        assert events_received[0].action == AutomationAction.ENABLE
        assert events_received[1].action == AutomationAction.DISABLE


class TestAutomationFileWatcherPolling:
    """Test polling behavior."""

    def test_respects_poll_interval(self, tmp_path):
        """Test that polling respects the configured interval."""
        toggle_file = tmp_path / "toggle.txt"
        log_file = tmp_path / "log.txt"
        event_bus = EventBus()

        events_received = []
        event_bus.subscribe(ToggleAutomationEvent, lambda e: events_received.append(e))

        # Use short interval for faster test
        watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path=str(toggle_file),
            log_file_path=str(log_file),
            poll_interval=2  # 2 seconds
        )

        watcher.start()

        # Write command
        toggle_file.write_text("ENABLE")

        # Wait less than poll interval - should not be processed yet
        time.sleep(1)
        assert len(events_received) == 0

        # Wait for full interval
        time.sleep(1.5)
        assert len(events_received) == 1

        watcher.stop()
