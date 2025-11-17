"""
Rate limiting utilities.

This module provides rate limiting middleware configuration for the API.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address


def create_limiter() -> Limiter:
    """
    Create and configure the rate limiter.

    Returns:
        Limiter: Configured rate limiter instance
    """
    return Limiter(
        key_func=get_remote_address,
        default_limits=["100/minute"]
    )
