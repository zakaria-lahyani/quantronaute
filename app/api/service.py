"""
API Service - Core service for managing API operations and EventBus integration.

This service provides the bridge between HTTP requests and the event-driven trading system.
"""

import logging
from typing import Optional

from app.infrastructure.event_bus import EventBus


class APIService:
    """
    Core API service for managing event-driven operations.

    This service coordinates between HTTP requests and the EventBus,
    implementing the correlation ID pattern for request-response tracking.
    """

    def __init__(
        self,
        event_bus: EventBus,
        logger: Optional[logging.Logger] = None
    ):
        """
        Initialize the API service.

        Args:
            event_bus: EventBus instance for publishing/subscribing to events
            logger: Optional logger instance
        """
        self.event_bus = event_bus
        self.logger = logger or logging.getLogger(__name__)

        self.logger.info("API Service initialized")

    def start(self):
        """Start the API service."""
        self.logger.info("API Service started")

    def stop(self):
        """Stop the API service."""
        self.logger.info("API Service stopped")
