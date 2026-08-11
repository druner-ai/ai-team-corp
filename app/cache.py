import time
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class TTLCache:
    """Simple in-memory cache with TTL."""

    def __init__(self, ttl: int = 600):
        self.ttl = ttl
        self._cache: dict[str, tuple[str, float]] = {}  # slug -> (url, expiry)

    def get(self, slug: str) -> Optional[str]:
        entry = self._cache.get(slug)
        if entry:
            url, expiry = entry
            if time.time() < expiry:
                return url
            else:
                if slug in self._cache:
                    del self._cache[slug]
        return None

    def set(self, slug: str, url: str):
        expiry = time.time() + self.ttl
        if expiry < time.time():  # Overflow check
            logger.warning(f"TTL overflow for slug: {slug}")
            expiry = float('inf')
        self._cache[slug] = (url, expiry)

    def delete(self, slug: str):
        if slug in self._cache:
            self._cache.pop(slug, None)
