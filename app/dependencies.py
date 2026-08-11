from app.database import DatabasePool
from app.cache import TTLCache
from app.services.link_service import LinkService
from app.utils import RateLimiter
from app.config import CACHE_TTL
import logging

logger = logging.getLogger(__name__)

# These module-level variables are set during application startup (or tests)
_db_pool: DatabasePool = None
_cache: TTLCache = None
_rate_limiter: RateLimiter = RateLimiter()


def get_db_pool() -> DatabasePool:
    if _db_pool is None:
        logger.error("Database pool not initialized")
        raise RuntimeError("Database pool not initialized")
    return _db_pool


def get_cache() -> TTLCache:
    if _cache is None:
        logger.error("Cache not initialized")
        raise RuntimeError("Cache not initialized")
    return _cache


def get_link_service() -> LinkService:
    if _db_pool is None or _cache is None:
        logger.error("Dependencies not initialized for LinkService")
        raise RuntimeError("Dependencies not initialized")
    return LinkService(_db_pool, _cache)


def get_rate_limiter() -> RateLimiter:
    if _rate_limiter is None:
        logger.error("Rate limiter not initialized")
        raise RuntimeError("Rate limiter not initialized")
    return _rate_limiter
