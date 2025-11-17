"""
Automation File Watcher for file-based automation control.

This module provides a file polling interface for controlling automation
through a simple text file (temporary Phase 1 interface).
"""

import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from app.events.automation_events import AutomationAction, ToggleAutomationEvent
from app.infrastructure.event_bus import EventBus


class AutomationFileWatcher:
    """
    File-based automation toggle interface (Phase 1).

    Polls a text file for automation commands and publishes ToggleAutomationEvent.
    This is a temporary interface that will be deprecated in Phase 2 when the
    REST API is implemented.

    Commands (case-insensitive):
    - ENABLE: Enable automated trading
    - DISABLE: Disable automated trading
    - QUERY: Query current automation state

    The watcher polls the file every N seconds (default: 5), reads the command,
    publishes the appropriate event, and logs the result.

    Example toggle file content:
        DISABLE

    Example:
        ```python
        event_bus = EventBus()
        file_watcher = AutomationFileWatcher(
            event_bus=event_bus,
            toggle_file_path="config/toggle_automation.txt",
            log_file_path="config/automation_log.txt",
            poll_interval=5
        )

        file_watcher.start()
        # Now the watcher polls the file every 5 seconds

        file_watcher.stop()
        ```
    """

    def __init__(
        self,
        event_bus: EventBus,
        toggle_file_path: str = "config/toggle_automation.txt",
        log_file_path: str = "config/automation_log.txt",
        poll_interval: int = 5,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize AutomationFileWatcher.

        Args:
            event_bus: EventBus for publishing toggle events
            toggle_file_path: Path to file containing toggle commands
            log_file_path: Path to log file for recording actions
            poll_interval: Polling interval in seconds (default: 5)
            logger: Optional logger instance
        """
        self.event_bus = event_bus
        self.toggle_file_path = Path(toggle_file_path)
        self.log_file_path = Path(log_file_path)
        self.poll_interval = poll_interval
        self.logger = logger or logging.getLogger(__name__)

        # Polling thread control
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._is_running = False

        # Last processed command to avoid duplicate processing
        self._last_command: Optional[str] = None
        self._last_modified_time: Optional[float] = None

        self.logger.info(
            f"AutomationFileWatcher initialized - "
            f"toggle_file={self.toggle_file_path}, "
            f"poll_interval={self.poll_interval}s"
        )

    def start(self) -> None:
        """
        Start the file watcher polling thread.

        Creates a daemon thread that polls the toggle file every poll_interval seconds.
        """
        if self._is_running:
            self.logger.warning("AutomationFileWatcher is already running")
            return

        self.logger.info("Starting AutomationFileWatcher...")

        # Create daemon thread for polling
        self._stop_event.clear()
        self._polling_thread = threading.Thread(
            target=self._polling_loop,
            name="AutomationFileWatcher",
            daemon=True  # Daemon thread will exit when main thread exits
        )
        self._polling_thread.start()
        self._is_running = True

        self.logger.info("AutomationFileWatcher started successfully")

    def stop(self) -> None:
        """
        Stop the file watcher polling thread gracefully.

        Signals the polling thread to stop and waits for it to finish.
        """
        if not self._is_running:
            self.logger.warning("AutomationFileWatcher is not running")
            return

        self.logger.info("Stopping AutomationFileWatcher...")

        # Signal thread to stop
        self._stop_event.set()

        # Wait for thread to finish (with timeout)
        if self._polling_thread and self._polling_thread.is_alive():
            self._polling_thread.join(timeout=self.poll_interval + 2)

        self._is_running = False
        self.logger.info("AutomationFileWatcher stopped")

    def _polling_loop(self) -> None:
        """
        Main polling loop that runs in a separate thread.

        Continuously polls the toggle file until stop is requested.
        """
        self.logger.debug("Polling loop started")

        while not self._stop_event.is_set():
            try:
                self._poll_file()
            except Exception as e:
                self.logger.error(f"Error in polling loop: {e}", exc_info=True)

            # Wait for poll_interval or until stop is requested
            self._stop_event.wait(self.poll_interval)

        self.logger.debug("Polling loop ended")

    def _poll_file(self) -> None:
        """
        Poll the toggle file and process commands.

        Checks if the file exists and has been modified since last check,
        reads the command, publishes event, and logs the result.
        """
        # Check if file exists
        if not self.toggle_file_path.exists():
            self.logger.debug(f"Toggle file does not exist: {self.toggle_file_path}")
            return

        try:
            # Get file modification time
            current_modified_time = os.path.getmtime(self.toggle_file_path)

            # Skip if file hasn't been modified since last check
            if self._last_modified_time is not None and current_modified_time <= self._last_modified_time:
                return

            # Update last modified time
            self._last_modified_time = current_modified_time

            # Read command from file (with retry for transient errors)
            command = self._read_command_with_retry(retries=3)

            if command is None:
                return

            # Skip if same command as last time (avoid duplicate processing)
            if command == self._last_command:
                self.logger.debug(f"Skipping duplicate command: {command}")
                return

            # Update last command
            self._last_command = command

            # Parse and publish event
            self._process_command(command)

        except Exception as e:
            self.logger.error(f"Error polling toggle file: {e}", exc_info=True)
            self._log_action("ERROR", f"Failed to poll file: {e}")

    def _read_command_with_retry(self, retries: int = 3) -> Optional[str]:
        """
        Read command from toggle file with retry logic.

        Args:
            retries: Number of retry attempts (default: 3)

        Returns:
            Command string (uppercase, stripped) or None if failed
        """
        for attempt in range(1, retries + 1):
            try:
                with open(self.toggle_file_path, 'r') as f:
                    content = f.read().strip().upper()

                if not content:
                    self.logger.debug("Toggle file is empty")
                    return None

                return content

            except Exception as e:
                if attempt < retries:
                    self.logger.warning(
                        f"Failed to read toggle file (attempt {attempt}/{retries}): {e}"
                    )
                    time.sleep(0.5)  # Brief delay before retry
                else:
                    self.logger.error(
                        f"Failed to read toggle file after {retries} attempts: {e}"
                    )
                    return None

        return None

    def _process_command(self, command: str) -> None:
        """
        Process a toggle command and publish appropriate event.

        Args:
            command: Command string (ENABLE, DISABLE, or QUERY)
        """
        # Parse command to action
        try:
            if command == "ENABLE":
                action = AutomationAction.ENABLE
            elif command == "DISABLE":
                action = AutomationAction.DISABLE
            elif command == "QUERY":
                action = AutomationAction.QUERY
            else:
                self.logger.warning(f"Invalid command in toggle file: '{command}'")
                self._log_action("ERROR", f"Invalid command: '{command}'")
                return

            # Publish toggle event
            event = ToggleAutomationEvent(
                action=action,
                reason=f"File toggle command: {command}",
                requested_by="file_watcher"
            )

            self.event_bus.publish(event)

            # Log successful action
            self.logger.info(
                f"📄 [FILE TOGGLE] Command '{command}' processed and event published"
            )
            self._log_action("SUCCESS", f"Command '{command}' processed")

        except Exception as e:
            self.logger.error(f"Error processing command '{command}': {e}", exc_info=True)
            self._log_action("ERROR", f"Failed to process command '{command}': {e}")

    def _log_action(self, status: str, message: str) -> None:
        """
        Log action to automation log file.

        Args:
            status: Action status (SUCCESS, ERROR, etc.)
            message: Log message
        """
        try:
            # Ensure log file directory exists
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

            # Create log entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"{timestamp} - {status} - {message}\n"

            # Append to log file
            with open(self.log_file_path, 'a') as f:
                f.write(log_entry)

            # Implement log rotation if file gets too large (10MB limit)
            self._rotate_log_if_needed()

        except Exception as e:
            self.logger.error(f"Failed to write to automation log file: {e}")

    def _rotate_log_if_needed(self, max_size_mb: int = 10) -> None:
        """
        Rotate log file if it exceeds maximum size.

        Args:
            max_size_mb: Maximum log file size in MB (default: 10)
        """
        try:
            if not self.log_file_path.exists():
                return

            # Check file size
            file_size_mb = self.log_file_path.stat().st_size / (1024 * 1024)

            if file_size_mb > max_size_mb:
                # Rotate: keep last 5 log files
                for i in range(4, 0, -1):
                    old_log = self.log_file_path.with_suffix(f'.txt.{i}')
                    new_log = self.log_file_path.with_suffix(f'.txt.{i + 1}')

                    if old_log.exists():
                        if new_log.exists():
                            new_log.unlink()
                        old_log.rename(new_log)

                # Rename current log to .1
                backup_log = self.log_file_path.with_suffix('.txt.1')
                if backup_log.exists():
                    backup_log.unlink()
                self.log_file_path.rename(backup_log)

                self.logger.info(f"Rotated automation log file (size: {file_size_mb:.2f}MB)")

        except Exception as e:
            self.logger.warning(f"Failed to rotate log file: {e}")

    def is_running(self) -> bool:
        """
        Check if file watcher is currently running.

        Returns:
            True if running, False otherwise
        """
        return self._is_running
