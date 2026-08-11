import random
import string
import time
from typing import Dict, Tuple
import logging

logger = logging.getLogger(__name__)


def generate_slug(length: int = 6) -> str:
    """Generate a random slug using base62 characters."""
    alphabet = string.ascii_letters + string.digits
    slug = ''.join(random.choices(alphabet, k=length))
    # Ensure uniqueness is checked by caller (LinkService)
    return slug


def mask_ip(ip: str) -> str:
    """Mask the last octet of an IPv4 address."""
    if not ip:
        return "unknown"
    # IPv4
    parts = ip.split('.')
    if len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts):
        parts[-1] = '0'
        return '.'.join(parts)
    # IPv6
    if ':' in ip:
        segments = ip.split(':')
        if len(segments) >= 2:
            segments[-1] = '0'
            return ':'.join(segments)
    # Fallback: mask last character
    logger.warning(f"Unrecognized IP format: {ip}")
    return ip[:-1] + '0' if len(ip) > 1 else '0'


class RateLimiter:
    """Simple in-memory fixed-window rate limiter."""

    def __init__(self):
        self._windows: Dict[str, Tuple[int, float]] = {}  # key -> (count, window_start)

    def is_allowed(self, key: str, limit: int, window: int = 60) -> bool:
        now = time.time()
        count, window_start = self._windows.get(key, (0, now))
        # Overflow check for time
        if now - window_start < 0:
            logger.warning(f"Time overflow detected for key: {key}")
            self._windows[key] = (1, now)
            return True
        if now - window_start > window:
            # New window
            self._windows[key] = (1, now)
            return True
        if count < limit:
            # Overflow check for count
            if count + 1 < 0:
                logger.warning(f"Count overflow detected for key: {key}")
                self._windows[key] = (limit, window_start)
                return False
            self._windows[key] = (count + 1, window_start)
            return True
        logger.warning(f"Rate limit denied for key: {key}")
        return False
