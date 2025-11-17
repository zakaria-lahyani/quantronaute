"""
Caching utilities for API responses.

This module provides caching utilities with TTL support for indicator
and account data that doesn't change frequently.
"""

import time
from typing import Dict, Any, Optional


class SimpleCache:
    """
    Simple in-memory cache with TTL support.

    Used to cache indicator values and account data to reduce
    EventBus traffic for high-frequency API requests.
    """

    def __init__(self, ttl: float = 5.0):
        """
        Initialize the cache.

        Args:
            ttl: Time-to-live in seconds (default: 5 seconds)
        """
        self.ttl = ttl
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Optional[Any]: Cached value or None if expired/missing
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if time.time() - entry["timestamp"] > self.ttl:
            del self._cache[key]
            return None

        return entry["value"]

    def set(self, key: str, value: Any) -> None:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._cache[key] = {
            "value": value,
            "timestamp": time.time()
        }

    def clear(self) -> None:
        """Clear all cached values."""
        self._cache.clear()

    def invalidate(self, key: str) -> None:
        """
        Invalidate a specific cache key.

        Args:
            key: Cache key to invalidate
        """
        if key in self._cache:
            del self._cache[key]
