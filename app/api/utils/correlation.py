"""
Correlation ID utilities for request-response tracking.

This module provides utilities for generating and tracking correlation IDs
to match HTTP requests with EventBus responses.
"""

import uuid


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID.

    Returns:
        str: A unique correlation ID (UUID4)
    """
    return str(uuid.uuid4())
