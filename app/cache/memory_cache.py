"""
In-memory cache with TTL support.

Provides a simple dictionary-based cache with per-entry expiration.
Thread-safe via asyncio.Lock.
"""

import asyncio
import time
from typing import Any, Optional


class MemoryCache:
    """
    Simple in-memory cache with TTL.

    Stores key-value pairs with an expiration timestamp.
    Expired entries are removed on access (lazy eviction).
    """

    def __init__(self, default_ttl: int = 300) -> None:
        """
        Initialize the cache.

        Args:
            default_ttl: Default time-to-live in seconds for cache entries.
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """
        Retrieve a value from the cache.

        Returns None if the key doesn't exist or the entry has expired.

        Args:
            key: The cache key.

        Returns:
            The cached value, or None.
        """
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None

            value, expires_at = entry
            if time.monotonic() > expires_at:
                del self._cache[key]
                return None

            return value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Store a value in the cache.

        Args:
            key: The cache key.
            value: The value to cache.
            ttl: Time-to-live in seconds. If None, uses default_ttl.
        """
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.monotonic() + effective_ttl

        async with self._lock:
            self._cache[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        """
        Remove a key from the cache.

        Args:
            key: The cache key to remove.
        """
        async with self._lock:
            self._cache.pop(key, None)

    # Synchronous wrappers for use in non-async contexts (e.g., service layer)
    def get(self, key: str) -> Optional[Any]:
        """Synchronous get (non-locking, for simple reads)."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if time.monotonic() > expires_at:
            del self._cache[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Synchronous set (non-locking, for simple writes)."""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        expires_at = time.monotonic() + effective_ttl
        self._cache[key] = (value, expires_at)

    def delete(self, key: str) -> None:
        """Synchronous delete."""
        self._cache.pop(key, None)
