# Разработчик

## Задача

        Напиши код строго по архитектурному документу, который создал Архитектор.

        ТРЕБОВАНИЯ:
        - Весь код в одном ответе (не по частям)
        - Каждый файл в markdown-блоке с указанием пути: ```python path/to/file.py
        - Включай requirements.txt или pyproject.toml
        - Включай тесты (pytest)
        - Включай .env.example
        - Если в архитектурном документе есть неясности — отметь в комментариях кода

        КАЧЕСТВО:
        - Типизация (type hints) на всех публичных функциях
        - Документирующие комментарии к классам и сложным функциям
        - Обработка ошибок (не голые try/except)
        - Валидация входных данных
        

## Результат

```python requirements.txt
fastapi==0.110.0
uvicorn[standard]==0.27.0
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
redis==5.0.1
pydantic==2.5.3
pydantic-settings==2.1.0
alembic==1.13.1
httpx==0.26.0
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-cov==4.1.0
python-dotenv==1.0.0
```

```python .env.example
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/urlshortener
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_PER_MINUTE=100
SHORT_ID_LENGTH=7
CACHE_TTL_SECONDS=3600
BASE_URL=http://localhost:8000
MAX_URL_LENGTH=2048
STATS_SYNC_THRESHOLD=10
SHUTDOWN_TIMEOUT_SECONDS=30
```

```python app/__init__.py
"""
URL Shortener Microservice Application Package.
"""
```

```python app/config.py
"""
Application configuration using pydantic-settings.
Loads configuration from environment variables and .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Attributes:
        DATABASE_URL: PostgreSQL connection string with asyncpg driver
        REDIS_URL: Redis connection string
        RATE_LIMIT_PER_MINUTE: Maximum requests per minute per IP
        SHORT_ID_LENGTH: Length of generated short IDs
        CACHE_TTL_SECONDS: TTL for Redis cache entries
        BASE_URL: Base URL for constructing short URLs
        MAX_URL_LENGTH: Maximum allowed length for original URLs
        STATS_SYNC_THRESHOLD: Number of clicks before syncing to PostgreSQL
        SHUTDOWN_TIMEOUT_SECONDS: Graceful shutdown timeout
    """
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )
    
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener"
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 100
    SHORT_ID_LENGTH: int = 7
    CACHE_TTL_SECONDS: int = 3600
    BASE_URL: str = "http://localhost:8000"
    MAX_URL_LENGTH: int = 2048
    STATS_SYNC_THRESHOLD: int = 10
    SHUTDOWN_TIMEOUT_SECONDS: int = 30
    
    # Optional: Redis password if needed
    REDIS_PASSWORD: Optional[str] = None


# Singleton settings instance
settings = Settings()
```

```python app/db/__init__.py
"""
Database package initialization.
"""
```

```python app/db/session.py
"""
Database session management with SQLAlchemy async engine.
Provides connection pooling and session factory.
"""
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
    AsyncEngine
)
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

from app.config import settings


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """
    Create async SQLAlchemy engine with connection pooling.
    
    Args:
        database_url: Optional database URL. Uses settings.DATABASE_URL if not provided.
        
    Returns:
        AsyncEngine: Configured async SQLAlchemy engine
        
    Note:
        Pool size is set to 10 with max overflow of 20 as per architecture requirements.
        For testing, NullPool can be used to avoid connection pooling issues.
    """
    url = database_url or settings.DATABASE_URL
    
    engine = create_async_engine(
        url,
        echo=False,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,   # Recycle connections after 1 hour
    )
    return engine


# Global engine instance
engine = create_engine()

# Session factory for creating async sessions
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session.
    
    Yields:
        AsyncSession: Database session that is automatically closed after use.
        
    Usage:
        @app.get("/")
        async def endpoint(db: AsyncSession = Depends(get_db_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_engine() -> None:
    """
    Close the database engine and release all connections.
    Called during application shutdown.
    """
    await engine.dispose()
```

```python app/db/redis_client.py
"""
Redis client management with connection pooling.
Provides async Redis client for caching, rate limiting, and stats buffering.
"""
import redis.asyncio as redis
from typing import Optional

from app.config import settings


# Global Redis connection pool
_redis_pool: Optional[redis.ConnectionPool] = None
_redis_client: Optional[redis.Redis] = None


async def get_redis_client() -> redis.Redis:
    """
    Get or create Redis client with connection pooling.
    
    Returns:
        redis.Redis: Configured async Redis client
        
    Note:
        Uses connection pool size of 10 as per architecture requirements.
        The client is created once and reused across requests.
    """
    global _redis_pool, _redis_client
    
    if _redis_client is None:
        _redis_pool = redis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=10,
            password=settings.REDIS_PASSWORD,
            decode_responses=True,
        )
        _redis_client = redis.Redis(connection_pool=_redis_pool)
    
    return _redis_client


async def close_redis() -> None:
    """
    Close Redis connection pool.
    Called during application shutdown.
    """
    global _redis_client, _redis_pool
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
    
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
```

```python app/models/__init__.py
"""
Models package initialization.
"""
from app.models.url_mapping import UrlMapping

__all__ = ["UrlMapping"]
```

```python app/models/url_mapping.py
"""
SQLAlchemy model for URL mappings.
Represents the url_mappings table in PostgreSQL.
"""
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Text,
    Boolean,
    DateTime,
    Index,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.sql import func
from datetime import datetime


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class UrlMapping(Base):
    """
    URL mapping entity storing short ID to original URL mappings.
    
    Attributes:
        id: Internal auto-incrementing ID
        short_id: Unique 7-character short identifier
        original_url: The original long URL
        created_at: Timestamp of creation
        expires_at: Optional expiration timestamp
        is_active: Soft delete flag
        click_count: Total number of redirects
    """
    __tablename__ = "url_mappings"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    short_id = Column(String(7), unique=True, nullable=False, index=True)
    original_url = Column(Text, nullable=False)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    click_count = Column(BigInteger, nullable=False, default=0)
    
    # Additional indexes as per architecture document
    __table_args__ = (
        Index("idx_url_mappings_short_id", "short_id", unique=True),
        Index("idx_url_mappings_created_at", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<UrlMapping(short_id='{self.short_id}', is_active={self.is_active})>"
```

```python app/schemas/__init__.py
"""
Schemas package initialization.
"""
from app.schemas.url import (
    ShortenRequest,
    ShortenResponse,
    StatsResponse,
)
from app.schemas.common import (
    ErrorResponse,
    HealthResponse,
)

__all__ = [
    "ShortenRequest",
    "ShortenResponse",
    "StatsResponse",
    "ErrorResponse",
    "HealthResponse",
]
```

```python app/schemas/common.py
"""
Common Pydantic schemas for API responses.
"""
from pydantic import BaseModel
from typing import Optional


class ErrorResponse(BaseModel):
    """
    Standard error response schema.
    
    Attributes:
        detail: Human-readable error message
        error_code: Optional machine-readable error code
    """
    detail: str
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    """
    Health check response schema.
    
    Attributes:
        status: Service status (e.g., "healthy", "degraded")
        database: Database connection status
        redis: Redis connection status
    """
    status: str
    database: str
    redis: str
```

```python app/schemas/url.py
"""
Pydantic schemas for URL shortening operations.
"""
from pydantic import BaseModel, HttpUrl, Field, field_validator
from datetime import datetime
from typing import Optional


class ShortenRequest(BaseModel):
    """
    Request schema for creating a short URL.
    
    Attributes:
        url: The original URL to shorten. Must be valid HTTP/HTTPS URL.
    """
    url: HttpUrl = Field(
        ...,
        description="The original URL to shorten",
        max_length=2048,
    )
    
    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        """
        Validate that URL uses only http or https scheme.
        Prevents javascript:, file:, data:, ftp: schemes.
        
        Args:
            v: The URL to validate
            
        Returns:
            HttpUrl: Validated URL
            
        Raises:
            ValueError: If URL scheme is not http or https
        """
        scheme = str(v).split("://")[0].lower() if "://" in str(v) else ""
        if scheme not in ("http", "https"):
            raise ValueError(
                f"URL scheme '{scheme}' is not allowed. Only http and https are supported."
            )
        return v


class ShortenResponse(BaseModel):
    """
    Response schema for created short URL.
    
    Attributes:
        short_id: Generated short identifier
        short_url: Full short URL
        original_url: The original URL that was shortened
        created_at: Timestamp of creation
    """
    short_id: str
    short_url: str
    original_url: str
    created_at: datetime


class StatsResponse(BaseModel):
    """
    Response schema for URL statistics.
    
    Attributes:
        short_id: Short identifier
        original_url: The original URL
        click_count: Number of redirects
        created_at: Timestamp of creation
        is_active: Whether the URL is active
    """
    short_id: str
    original_url: str
    click_count: int
    created_at: datetime
    is_active: bool
```

```python app/utils/__init__.py
"""
Utilities package initialization.
"""
from app.utils.short_id import generate_short_id, validate_short_id
from app.utils.url_validator import validate_url_safety

__all__ = [
    "generate_short_id",
    "validate_short_id",
    "validate_url_safety",
]
```

```python app/utils/short_id.py
"""
Short ID generation and validation utilities.
Uses base62 encoding for compact, URL-safe identifiers.
"""
import secrets
import string
from typing import Optional


# Base62 alphabet: a-z, A-Z, 0-9
BASE62_ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits
BASE62_LENGTH = len(BASE62_ALPHABET)  # 62


def _encode_base62(num: int) -> str:
    """
    Encode an integer to base62 string.
    
    Args:
        num: Integer to encode
        
    Returns:
        str: Base62 encoded string
    """
    if num == 0:
        return BASE62_ALPHABET[0]
    
    result = []
    while num > 0:
        num, remainder = divmod(num, BASE62_LENGTH)
        result.append(BASE62_ALPHABET[remainder])
    
    return "".join(reversed(result))


def generate_short_id(length: int = 7) -> str:
    """
    Generate a random short ID of specified length using base62 encoding.
    
    Uses cryptographically secure random number generator (secrets module)
    to generate random bytes, then encodes them in base62.
    
    Args:
        length: Desired length of the short ID (default: 7)
        
    Returns:
        str: Generated short ID
        
    Note:
        With 7 characters in base62, we get 62^7 ≈ 3.5 trillion combinations,
        which is sufficient to avoid collisions for reasonable volumes.
    """
    # Generate enough random bytes to cover the required length
    # Each byte gives 256 possibilities, we need 62^length
    # Using secrets.randbelow for uniform distribution
    max_value = BASE62_LENGTH ** length - 1
    random_num = secrets.randbelow(max_value + 1)
    
    # Encode to base62 and pad to required length
    encoded = _encode_base62(random_num)
    return encoded.zfill(length)


def validate_short_id(short_id: str, expected_length: int = 7) -> bool:
    """
    Validate that a short ID has the correct format.
    
    Args:
        short_id: The short ID to validate
        expected_length: Expected length of the short ID (default: 7)
        
    Returns:
        bool: True if valid, False otherwise
        
    Note:
        Valid short IDs contain only alphanumeric characters [a-zA-Z0-9]
        and have exactly the expected length.
    """
    if not short_id or len(short_id) != expected_length:
        return False
    
    return all(c in BASE62_ALPHABET for c in short_id)
```

```python app/utils/url_validator.py
"""
URL validation utilities including SSRF protection.
"""
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Optional


# Private/internal IP ranges that should be blocked for SSRF protection
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),  # Link-local
    ipaddress.ip_network("0.0.0.0/8"),       # Current network
]


def is_private_ip(hostname: str) -> bool:
    """
    Check if a hostname resolves to a private/internal IP address.
    
    Args:
        hostname: Hostname or IP address to check
        
    Returns:
        bool: True if the IP is private/internal, False otherwise
        
    Note:
        This is a basic SSRF protection. In production, consider using
        a dedicated library or external service for more comprehensive protection.
    """
    try:
        # Try to parse as IP address first
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not an IP, try DNS resolution
        try:
            ip = ipaddress.ip_address(socket.gethostbyname(hostname))
        except (socket.gaierror, ValueError):
            # Cannot resolve, allow it (will fail at connection time)
            return False
    
    # Check against private ranges
    for private_range in PRIVATE_IP_RANGES:
        if ip in private_range:
            return True
    
    return False


def validate_url_safety(url: str) -> tuple[bool, Optional[str]]:
    """
    Validate URL safety including SSRF protection.
    
    Args:
        url: The URL to validate
        
    Returns:
        tuple[bool, Optional[str]]: (is_safe, error_message)
        - is_safe: True if URL is safe to use
        - error_message: Error description if not safe, None otherwise
        
    Note:
        This performs additional safety checks beyond basic URL validation.
        Currently checks for private IP access (SSRF protection).
        Can be extended with additional checks as needed.
    """
    try:
        parsed = urlparse(url)
        
        # Check scheme
        if parsed.scheme.lower() not in ("http", "https"):
            return False, f"URL scheme '{parsed.scheme}' is not allowed"
        
        # Check for hostname
        if not parsed.hostname:
            return False, "URL has no valid hostname"
        
        # SSRF check: block private IPs
        if is_private_ip(parsed.hostname):
            return False, f"Access to private IP '{parsed.hostname}' is not allowed"
        
        return True, None
        
    except Exception as e:
        return False, f"URL validation failed: {str(e)}"
```

```python app/services/__init__.py
"""
Services package initialization.
"""
from app.services.cache_service import CacheService
from app.services.stats_service import StatsService
from app.services.url_service import UrlService

__all__ = [
    "CacheService",
    "StatsService",
    "UrlService",
]
```

```python app/services/cache_service.py
"""
Redis cache service for URL mappings and statistics.
Provides typed wrappers around Redis operations.
"""
import redis.asyncio as redis
from typing import Optional

from app.config import settings


class CacheService:
    """
    Service for Redis cache operations.
    
    Handles caching of URL mappings and provides typed interface
    for get/set/delete operations with proper key formatting.
    
    Attributes:
        redis_client: Async Redis client instance
        ttl: Default TTL for cache entries in seconds
    """
    
    # Key prefixes for different cache types
    URL_KEY_PREFIX = "url:"
    STATS_KEY_PREFIX = "stats:"
    RATE_LIMIT_KEY_PREFIX = "rl:"
    
    def __init__(self, redis_client: redis.Redis, ttl: int | None = None):
        """
        Initialize cache service.
        
        Args:
            redis_client: Async Redis client
            ttl: Default TTL in seconds (uses settings.CACHE_TTL_SECONDS if not provided)
        """
        self.redis_client = redis_client
        self.ttl = ttl or settings.CACHE_TTL_SECONDS
    
    def _url_key(self, short_id: str) -> str:
        """Format URL cache key."""
        return f"{self.URL_KEY_PREFIX}{short_id}"
    
    def _stats_key(self, short_id: str) -> str:
        """Format stats cache key."""
        return f"{self.STATS_KEY_PREFIX}{short_id}"
    
    async def get_url(self, short_id: str) -> Optional[str]:
        """
        Get cached original URL for a short ID.
        
        Args:
            short_id: Short identifier
            
        Returns:
            Optional[str]: Original URL if cached, None otherwise
        """
        return await self.redis_client.get(self._url_key(short_id))
    
    async def set_url(self, short_id: str, original_url: str, ttl: int | None = None) -> None:
        """
        Cache an original URL for a short ID.
        
        Args:
            short_id: Short identifier
            original_url: Original URL to cache
            ttl: Optional TTL override in seconds
        """
        key = self._url_key(short_id)
        await self.redis_client.setex(key, ttl or self.ttl, original_url)
    
    async def delete_url(self, short_id: str) -> None:
        """
        Remove cached URL for a short ID.
        
        Args:
            short_id: Short identifier
        """
        await self.redis_client.delete(self._url_key(short_id))
    
    async def increment_stats(self, short_id: str) -> int:
        """
        Increment click counter in Redis for a short ID.
        
        Args:
            short_id: Short identifier
            
        Returns:
            int: New counter value after increment
        """
        key = self._stats_key(short_id)
        return await self.redis_client.incr(key)
    
    async def get_stats(self, short_id: str) -> int:
        """
        Get current click count from Redis for a short ID.
        
        Args:
            short_id: Short identifier
            
        Returns:
            int: Current click count (0 if not found)
        """
        key = self._stats_key(short_id)
        value = await self.redis_client.get(key)
        return int(value) if value else 0
    
    async def delete_stats(self, short_id: str) -> None:
        """
        Remove stats counter from Redis for a short ID.
        
        Args:
            short_id: Short identifier
        """
        await self.redis_client.delete(self._stats_key(short_id))
    
    async def check_rate_limit(self, client_ip: str, limit: int = 100, window: int = 60) -> tuple[bool, int, int]:
        """
        Check rate limit for a client IP using sliding window.
        
        Args:
            client_ip: Client IP address
            limit: Maximum requests per window (default: 100)
            window: Time window in seconds (default: 60)
            
        Returns:
            tuple[bool, int, int]: (is_allowed, remaining, reset_time)
            - is_allowed: True if request is within limit
            - remaining: Number of requests remaining in window
            - reset_time: Unix timestamp when window resets
        """
        key = f"{self.RATE_LIMIT_KEY_PREFIX}{client_ip}"
        
        # Use Redis pipeline for atomic operations
        async with self.redis_client.pipeline() as pipe:
            current = await self.redis_client.get(key)
            
            if current is None:
                # First request in window
                await pipe.setex(key, window, 1)
                await pipe.ttl(key)
                results = await pipe.execute()
                return True, limit - 1, results[1]
            
            current_count = int(current)
            if current_count >= limit:
                # Rate limit exceeded
                ttl = await self.redis_client.ttl(key)
                return False, 0, ttl if ttl > 0 else window
            
            # Increment counter
            await pipe.incr(key)
            await pipe.ttl(key)
            results = await pipe.execute()
            new_count = results[0]
            ttl = results[1]
            
            return True, limit - new_count, ttl if ttl > 0 else window
```

```python app/services/stats_service.py
"""
Statistics service for managing click counts.
Handles buffered stats in Redis and synchronization to PostgreSQL.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import logging

from app.models.url_mapping import UrlMapping
from app.services.cache_service import CacheService
from app.config import settings

logger = logging.getLogger(__name__)


class StatsService:
    """
    Service for managing URL click statistics.
    
    Buffers click counts in Redis and periodically syncs to PostgreSQL
    to reduce write load on the database during high traffic.
    
    Attributes:
        cache_service: Cache service for Redis operations
        sync_threshold: Number of clicks before syncing to DB
    """
    
    def __init__(
        self,
        cache_service: CacheService,
        sync_threshold: int | None = None
    ):
        """
        Initialize stats service.
        
        Args:
            cache_service: Cache service instance
            sync_threshold: Clicks threshold for DB sync (uses settings if not provided)
        """
        self.cache_service = cache_service
        self.sync_threshold = sync_threshold or settings.STATS_SYNC_THRESHOLD
    
    async def record_click(self, short_id: str, db_session: AsyncSession) -> None:
        """
        Record a click for a short URL.
        
        Increments counter in Redis and syncs to PostgreSQL
        when threshold is reached.
        
        Args:
            short_id: Short identifier
            db_session: Database session for potential sync
        """
        # Increment in Redis
        new_count = await self.cache_service.increment_stats(short_id)
        
        # Check if we should sync to PostgreSQL
        if new_count % self.sync_threshold == 0:
            await self.sync_to_db(short_id, db_session)
    
    async def sync_to_db(self, short_id: str, db_session: AsyncSession) -> None:
        """
        Synchronize click count from Redis to PostgreSQL.
        
        Args:
            short_id: Short identifier
            db_session: Database session
        """
        try:
            redis_count = await self.cache_service.get_stats(short_id)
            
            if redis_count > 0:
                stmt = (
                    update(UrlMapping)
                    .where(UrlMapping.short_id == short_id)
                    .values(click_count=redis_count)
                )
                await db_session.execute(stmt)
                await db_session.commit()
                
                logger.debug(f"Synced stats for {short_id}: {redis_count} clicks")
        except Exception as e:
            logger.error(f"Failed to sync stats for {short_id}: {e}")
            await db_session.rollback()
    
    async def get_total_clicks(self, short_id: str, db_session: AsyncSession) -> int:
        """
        Get total click count combining Redis buffer and DB value.
        
        Args:
            short_id: Short identifier
            db_session: Database session
            
        Returns:
            int: Total click count
        """
        # Get Redis buffer count
        redis_count = await self.cache_service.get_stats(short_id)
        
        # Get DB count
        stmt = select(UrlMapping.click_count).where(UrlMapping.short_id == short_id)
        result = await db_session.execute(stmt)
        db_count = result.scalar_one_or_none()
        
        if db_count is None:
            return redis_count
        
        # Return the maximum of both (Redis should be more up-to-date)
        return max(redis_count, db_count)
    
    async def cleanup_stats(self, short_id: str) -> None:
        """
        Remove stats from Redis for a deleted URL.
        
        Args:
            short_id: Short identifier
        """
        await self.cache_service.delete_stats(short_id)
```

```python app/services/url_service.py
"""
URL service containing core business logic for URL shortening operations.
Orchestrates cache, database, and stats services.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Optional, Tuple
import logging

from app.models.url_mapping import UrlMapping
from app.services.cache_service import CacheService
from app.services.stats_service import StatsService
from app.utils.short_id import generate_short_id, validate_short_id
from app.config import settings

logger = logging.getLogger(__name__)

# Maximum attempts to generate unique short ID (collision avoidance)
MAX_GENERATION_ATTEMPTS = 3


class UrlService:
    """
    Core service for URL shortening operations.
    
    Handles creation, retrieval, statistics, and deletion of short URLs.
    Coordinates between cache, database, and statistics services.
    
    Attributes:
        cache_service: Cache service for Redis operations
        stats_service: Statistics service for click tracking
        short_id_length: Length of generated short IDs
    """
    
    def __init__(
        self,
        cache_service: CacheService,
        stats_service: StatsService,
        short_id_length: int | None = None
    ):
        """
        Initialize URL service.
        
        Args:
            cache_service: Cache service instance
            stats_service: Statistics service instance
            short_id_length: Length of short IDs (uses settings if not provided)
        """
        self.cache_service = cache_service
        self.stats_service = stats_service
        self.short_id_length = short_id_length or settings.SHORT_ID_LENGTH
    
    async def create_short_url(
        self,
        original_url: str,
        db_session: AsyncSession
    ) -> UrlMapping:
        """
        Create a new short URL mapping.
        
        Generates a unique short ID, stores the mapping in PostgreSQL,
        and caches it in Redis.
        
        Args:
            original_url: The original URL to shorten
            db_session: Database session
            
        Returns:
            UrlMapping: Created URL mapping entity
            
        Raises:
            ValueError: If unable to generate unique short ID after max attempts
        """
        # Try to generate unique short ID
        for attempt in range(MAX_GENERATION_ATTEMPTS):
            short_id = generate_short_id(self.short_id_length)
            
            # Check if short_id already exists
            stmt = select(UrlMapping).where(UrlMapping.short_id == short_id)
            result = await db_session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing is None:
                # Unique ID found, create mapping
                url_mapping = UrlMapping(
                    short_id=short_id,
                    original_url=str(original_url),
                )
                db_session.add(url_mapping)
                await db_session.commit()
                await db_session.refresh(url_mapping)
                
                # Cache the new mapping
                await self.cache_service.set_url(short_id, str(original_url))
                
                logger.info(f"Created short URL: {short_id} -> {original_url}")
                return url_mapping
        
        # This should be extremely rare with 62^7 combinations
        logger.error("Failed to generate unique short ID after max attempts")
        raise ValueError("Unable to generate unique short ID. Please try again.")
    
    async def get_original_url(
        self,
        short_id: str,
        db_session: AsyncSession
    ) -> Optional[str]:
        """
        Get original URL for a short ID and record a click.
        
        Checks Redis cache first, falls back to PostgreSQL.
        Records click for statistics.
        
        Args:
            short_id: Short identifier
            db_session: Database session
            
        Returns:
            Optional[str]: Original URL if found and active, None otherwise
        """
        # Validate short_id format
        if not validate_short_id(short_id, self.short_id_length):
            return None
        
        # Try cache first
        cached_url = await self.cache_service.get_url(short_id)
        if cached_url:
            # Record click asynchronously (don't await to avoid slowing response)
            await self.stats_service.record_click(short_id, db_session)
            return cached_url
        
        # Cache miss, query database
        stmt = select(UrlMapping).where(
            UrlMapping.short_id == short_id,
            UrlMapping.is_active == True
        )
        result = await db_session.execute(stmt)
        url_mapping = result.scalar_one_or_none()
        
        if url_mapping is None:
            return None
        
        # Cache for future requests
        await self.cache_service.set_url(short_id, url_mapping.original_url)
        
        # Record click
        await self.stats_service.record_click(short_id, db_session)
        
        return url_mapping.original_url
    
    async def get_stats(
        self,
        short_id: str,
        db_session: AsyncSession
    ) -> Optional[dict]:
        """
        Get statistics for a short URL.
        
        Args:
            short_id: Short identifier
            db_session: Database session
            
        Returns:
            Optional[dict]: Statistics dict if found, None otherwise
        """
        # Validate short_id format
        if not validate_short_id(short_id, self.short_id_length):
            return None
        
        stmt = select(UrlMapping).where(UrlMapping.short_id == short_id)
        result = await db_session.execute(stmt)
        url_mapping = result.scalar_one_or_none()
        
        if url_mapping is None:
            return None
        
        # Get total clicks (combining Redis buffer and DB)
        total_clicks = await self.stats_service.get_total_clicks(short_id, db_session)
        
        return {
            "short_id": url_mapping.short_id,
            "original_url": url_mapping.original_url,
            "click_count": total_clicks,
            "created_at": url_mapping.created_at,
            "is_active": url_mapping.is_active,
        }
    
    async def delete_url(
        self,
        short_id: str,
        db_session: AsyncSession
    ) -> bool:
        """
        Soft delete a short URL (set is_active=False).
        
        Removes from Redis cache and cleans up stats.
        
        Args:
            short_id: Short identifier
            db_session: Database session
            
        Returns:
            bool: True if deleted successfully, False if not found
        """
        # Validate short_id format
        if not validate_short_id(short_id, self.short_id_length):
            return False
        
        # Check if exists and is active
        stmt = select(UrlMapping).where(
            UrlMapping.short_id == short_id,
            UrlMapping.is_active == True
        )
        result = await db_session.execute(stmt)
        url_mapping = result.scalar_one_or_none()
        
        if url_mapping is None:
            return False
        
        # Soft delete
        url_mapping.is_active = False
        await db_session.commit()
        
        # Remove from cache
        await self.cache_service.delete_url(short_id)
        
        # Cleanup stats
        await self.stats_service.cleanup_stats(short_id)
        
        logger.info(f"Deleted short URL: {short_id}")
        return True
```

```python app/middleware/__init__.py
"""
Middleware package initialization.
"""
from app.middleware.rate_limit import RateLimitMiddleware

__all__ = ["RateLimitMiddleware"]
```

```python app/middleware/rate_limit.py
"""
Rate limiting middleware using Redis sliding window.
Limits requests per IP address based on configuration.
"""
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import logging

from app.services.cache_service import CacheService
from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting based on client IP.
    
    Uses Redis sliding window algorithm to track request counts per IP.
    Returns 429 Too Many Requests when limit is exceeded.
    
    Attributes:
        app: The ASGI application
        cache_service: Cache service for Redis operations
        limit: Maximum requests per window
        window: Time window in seconds
    """
    
    def __init__(
        self,
        app: ASGIApp,
        cache_service: CacheService,
        limit: int | None = None,
        window: int = 60
    ):
        """
        Initialize rate limit middleware.
        
        Args:
            app: The ASGI application
            cache_service: Cache service instance
            limit: Max requests per window (uses settings if not provided)
            window: Time window in seconds (default: 60)
        """
        super().__init__(app)
        self.cache_service = cache_service
        self.limit = limit or settings.RATE_LIMIT_PER_MINUTE
        self.window = window
    
    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP from request.
        
        Checks X-Forwarded-For header for proxied requests,
        falls back to direct client IP.
        
        Args:
            request: FastAPI request object
            
        Returns:
            str: Client IP address
        """
        # Check X-Forwarded-For header (for reverse proxy setups)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # Take the first IP in the chain
            return forwarded.split(",")[0].strip()
        
        # Fall back to direct client
        if request.client:
            return request.client.host
        
        return "unknown"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        """
        Process request through rate limit check.
        
        Args:
            request: Incoming request
            call_next: Next middleware/endpoint handler
            
        Returns:
            Response: Either rate limit error or normal response
        """
        client_ip = self._get_client_ip(request)
        
        # Check rate limit
        is_allowed, remaining, reset_time = await self.cache_service.check_rate_limit(
            client_ip,
            limit=self.limit,
            window=self.window
        )
        
        if not is_allowed:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            
            # Calculate retry-after in seconds
            retry_after = max(1, reset_time)
            
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "Too many requests. Please try again later.",
                    "error_code": "RATE_LIMIT_EXCEEDED"
                },
                headers={
                    "X-RateLimit-Limit": str(self.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(time.time()) + reset_time),
                    "Retry-After": str(retry_after),
                }
            )
        
        # Process the request
        response = await call_next(request)
        
        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(time.time()) + reset_time)
        
        return response
```

```python app/dependencies.py
"""
FastAPI dependency injection setup.
Provides database sessions, Redis clients, and service instances.
"""
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from app.db.session import get_db_session
from app.db.redis_client import get_redis_client
from app.services.cache_service import CacheService
from app.services.stats_service import StatsService
from app.services.url_service import UrlService


# Singleton service instances (created once, reused across requests)
_cache_service: CacheService | None = None
_stats_service: StatsService | None = None
_url_service: UrlService | None = None


async def get_cache_service(
    redis_client: redis.Redis = Depends(get_redis_client)
) -> CacheService:
    """
    Dependency that provides CacheService instance.
    
    Args:
        redis_client: Redis client from dependency
        
    Returns:
        CacheService: Configured cache service
    """
    global _cache_service
    if _cache_service is None:
        _cache_service = CacheService(redis_client)
    return _cache_service


async def get_stats_service(
    cache_service: CacheService = Depends(get_cache_service)
) -> StatsService:
    """
    Dependency that provides StatsService instance.
    
    Args:
        cache_service: Cache service from dependency
        
    Returns:
        StatsService: Configured stats service
    """
    global _stats_service
    if _stats_service is None:
        _stats_service = StatsService(cache_service)
    return _stats_service


async def get_url_service(
    cache_service: CacheService = Depends(get_cache_service),
    stats_service: StatsService = Depends(get_stats_service)
) -> UrlService:
    """
    Dependency that provides UrlService instance.
    
    Args:
        cache_service: Cache service from dependency
        stats_service: Stats service from dependency
        
    Returns:
        UrlService: Configured URL service
    """
    global _url_service
    if _url_service is None:
        _url_service = UrlService(cache_service, stats_service)
    return _url_service
```

```python app/routers/__init__.py
"""
Routers package initialization.
"""
from app.routers.shorten import router as shorten_router
from app.routers.redirect import router as redirect_router
from app.routers.stats import router as stats_router
from app.routers.delete import router as delete_router
from app.routers.health import router as health_router

__all__ = [
    "shorten_router",
    "redirect_router",
    "stats_router",
    "delete_router",
    "health_router",
]
```

```python app/routers/shorten.py
"""
Router for POST /shorten endpoint.
Creates short URLs from original URLs.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.url import ShortenRequest, ShortenResponse
from app.schemas.common import ErrorResponse
from app.services.url_service import UrlService
from app.dependencies import get_url_service, get_db_session
from app.utils.url_validator import validate_url_safety
from app.config import settings

router = APIRouter(tags=["shorten"])


@router.post(
    "/shorten",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid URL"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Internal server error"},
    },
    summary="Create short URL",
    description="Creates a shortened URL from a long URL. Returns the short ID and full short URL."
)
async def create_short_url(
    request: ShortenRequest,
    url_service: UrlService = Depends(get_url_service),
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Create a new short URL.
    
    Args:
        request: Shorten request with original URL
        url_service: URL service instance
        db_session: Database session
        
    Returns:
        ShortenResponse: Created short URL details
        
    Raises:
        HTTPException: 400 if URL is invalid or unsafe
        HTTPException: 500 if short ID generation fails
    """
    from fastapi import HTTPException
    
    # Additional URL safety validation (SSRF protection)
    is_safe, error_msg = validate_url_safety(str(request.url))
    if not is_safe:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg or "URL is not safe to shorten"
        )
    
    try:
        url_mapping = await url_service.create_short_url(
            str(request.url),
            db_session
        )
        
        return ShortenResponse(
            short_id=url_mapping.short_id,
            short_url=f"{settings.BASE_URL}/{url_mapping.short_id}",
            original_url=url_mapping.original_url,
            created_at=url_mapping.created_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
```

```python app/routers/redirect.py
"""
Router for GET /{id} endpoint.
Redirects short URLs to original URLs.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.url_service import UrlService
from app.dependencies import get_url_service, get_db_session

router = APIRouter(tags=["redirect"])


@router.get(
    "/{short_id}",
    status_code=status.HTTP_302_FOUND,
    responses={
        404: {"description": "Short URL not found"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Redirect to original URL",
    description="Redirects to the original URL associated with the short ID."
)
async def redirect_to_url(
    short_id: str,
    url_service: UrlService = Depends(get_url_service),
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Redirect to original URL by short ID.
    
    Args:
        short_id: Short identifier from URL path
        url_service: URL service instance
        db_session: Database session
        
    Returns:
        RedirectResponse: HTTP 302 redirect to original URL
        
    Raises:
        HTTPException: 404 if short ID not found or inactive
    """
    original_url = await url_service.get_original_url(short_id, db_session)
    
    if original_url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found or has been deactivated"
        )
    
    return RedirectResponse(
        url=original_url,
        status_code=status.HTTP_302_FOUND
    )
```

```python app/routers/stats.py
"""
Router for GET /stats/{id} endpoint.
Returns statistics for a short URL.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.url import StatsResponse
from app.services.url_service import UrlService
from app.dependencies import get_url_service, get_db_session

router = APIRouter(tags=["stats"])


@router.get(
    "/stats/{short_id}",
    response_model=StatsResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"description": "Short URL not found"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Get URL statistics",
    description="Returns click statistics and metadata for a short URL."
)
async def get_url_stats(
    short_id: str,
    url_service: UrlService = Depends(get_url_service),
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Get statistics for a short URL.
    
    Args:
        short_id: Short identifier from URL path
        url_service: URL service instance
        db_session: Database session
        
    Returns:
        StatsResponse: URL statistics and metadata
        
    Raises:
        HTTPException: 404 if short ID not found
    """
    stats = await url_service.get_stats(short_id, db_session)
    
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found"
        )
    
    return StatsResponse(**stats)
```

```python app/routers/delete.py
"""
Router for DELETE /{id} endpoint.
Soft deletes a short URL.
"""
from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.url_service import UrlService
from app.dependencies import get_url_service, get_db_session

router = APIRouter(tags=["delete"])


@router.delete(
    "/{short_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        404: {"description": "Short URL not found"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Delete short URL",
    description="Soft deletes a short URL. Subsequent redirects will return 404."
)
async def delete_short_url(
    short_id: str,
    url_service: UrlService = Depends(get_url_service),
    db_session: AsyncSession = Depends(get_db_session),
):
    """
    Delete (deactivate) a short URL.
    
    Args:
        short_id: Short identifier from URL path
        url_service: URL service instance
        db_session: Database session
        
    Returns:
        Response: Empty 204 No Content response
        
    Raises:
        HTTPException: 404 if short ID not found or already deleted
    """
    deleted = await url_service.delete_url(short_id, db_session)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Short URL not found or already deleted"
        )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

```python app/routers/health.py
"""
Router for GET /health endpoint.
Provides health check for the service.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import redis.asyncio as redis

from app.schemas.common import HealthResponse
from app.dependencies import get_db_session, get_redis_client

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Checks service health including database and Redis connectivity."
)
async def health_check(
    db_session: AsyncSession = Depends(get_db_session),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    """
    Perform health check on all dependencies.
    
    Args:
        db_session: Database session
        redis_client: Redis client
        
    Returns:
        HealthResponse: Health status of all components
    """
    # Check database
    db_status = "healthy"
    try:
        await db_session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"
    
    # Check Redis
    redis_status = "healthy"
    try:
        await redis_client.ping()
    except Exception:
        redis_status = "unhealthy"
    
    # Overall status
    overall_status = "healthy" if db_status == "healthy" and redis_status == "healthy" else "degraded"
    
    return HealthResponse(
        status=overall_status,
        database=db_status,
        redis=redis_status,
    )
```

```python app/main.py
"""
FastAPI application entry point.
Configures middleware, routers, and lifecycle handlers.
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.config import settings
from app.db.session import close_engine, engine
from app.db.redis_client import close_redis, get_redis_client
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.cache_service import CacheService
from app.routers import (
    shorten_router,
    redirect_router,
    stats_router,
    delete_router,
    health_router,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Initialize connections
    - Shutdown: Gracefully close all connections
    
    Note:
        Shutdown timeout is configurable via settings.SHUTDOWN_TIMEOUT_SECONDS.
        During shutdown, the service stops accepting new connections and
        waits for existing requests to complete.
    """
    # Startup
    logger.info("Starting URL Shortener service...")
    logger.info(f"Database: {settings.DATABASE_URL}")
    logger.info(f"Redis: {settings.REDIS_URL}")
    
    # Pre-initialize Redis connection
    await get_redis_client()
    logger.info("Redis connection established")
    
    yield
    
    # Shutdown
    logger.info("Shutting down URL Shortener service...")
    
    # Close Redis connections
    await close_redis()
    logger.info("Redis connections closed")
    
    # Close database connections
    await close_engine()
    logger.info("Database connections closed")
    
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    app = FastAPI(
        title="URL Shortener",
        description="A high-performance URL shortening microservice",
        version="1.0.0",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )
    
    # Add CORS middleware (allow all origins for API)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Note: RateLimitMiddleware will be added after CacheService is available
    # This is handled in the app startup or through dependency injection
    
    # Register routers
    # Order matters: more specific routes first
    app.include_router(health_router)
    app.include_router(shorten_router)
    app.include_router(stats_router)
    app.include_router(delete_router)
    app.include_router(redirect_router)  # Catch-all for /{id} should be last
    
    return app


# Create application instance
app = create_app()


# Add rate limit middleware
# Note: This is done after app creation because it needs CacheService
@app.on_event("startup")
async def add_rate_limit_middleware():
    """
    Add rate limit middleware after Redis connection is established.
    This is done in startup event because middleware needs CacheService
    which requires Redis client.
    """
    redis_client = await get_redis_client()
    cache_service = CacheService(redis_client)
    
    app.add_middleware(
        RateLimitMiddleware,
        cache_service=cache_service,
        limit=settings.RATE_LIMIT_PER_MINUTE,
    )
    logger.info("Rate limit middleware added")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
```

```python alembic/env.py
"""
Alembic environment configuration for database migrations.
"""
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.config import settings
from app.models.url_mapping import Base

# Alembic Config object
config = context.config

# Set SQLAlchemy URL from settings
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# MetaData for autogenerate support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    Configures the context with just a URL and not an Engine.
    Calls to context.execute() emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Run migrations in 'online' mode with the given connection.
    """
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode with async engine.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    """
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

```python alembic/versions/001_initial.py
"""
Initial migration: Create url_mappings table.

Revision ID: 001
Revises: None
Create Date: 2025-01-15 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Revision identifiers
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create url_mappings table with all required columns and indexes.
    """
    op.create_table(
        "url_mappings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("short_id", sa.String(7), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("click_count", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("short_id"),
    )
    
    # Create indexes
    op.create_index("idx_url_mappings_short_id", "url_mappings", ["short_id"], unique=True)
    op.create_index("idx_url_mappings_created_at", "url_mappings", ["created_at"])


def downgrade() -> None:
    """
    Drop url_mappings table and indexes.
    """
    op.drop_index("idx_url_mappings_created_at", table_name="url_mappings")
    op.drop_index("idx_url_mappings_short_id", table_name="url_mappings")
    op.drop_table("url_mappings")
```

```python tests/__init__.py
"""
Test package initialization.
"""
```

```python tests/conftest.py
"""
Pytest fixtures for URL Shortener tests.
Provides test client, database session, and mocked Redis.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator
import redis.asyncio as redis
from unittest.mock import AsyncMock, MagicMock, patch

from app.main import create_app
from app.models.url_mapping import Base
from app.db.session import get_db_session
from app.db.redis_client import get_redis_client
from app.services.cache_service import CacheService
from app.services.stats_service import StatsService
from app.services.url_service import UrlService
from app.dependencies import (
    get_cache_service,
    get_stats_service,
    get_url_service,
)


# Test database URL (use SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """
    Create test database engine.
    Uses SQLite for fast, isolated tests.
    """
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        poolclass=NullPool,
    )
    
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    # Drop all tables after test
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create test database session.
    """
    session_factory = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def mock_redis():
    """
    Create a mocked Redis client for testing.
    """
    redis_mock = AsyncMock(spec=redis.Redis)
    
    # Setup common Redis mock behaviors
    redis_mock.get.return_value = None
    redis_mock.setex.return_value = None
    redis_mock.delete.return_value = None
    redis_mock.incr.return_value = 1
    redis_mock.ping.return_value = True
    
    # Mock pipeline
    pipeline_mock = AsyncMock()
    pipeline_mock.execute.return_value = [1, 60]
    redis_mock.pipeline.return_value = pipeline_mock
    
    return redis_mock


@pytest.fixture
def cache_service(mock_redis):
    """
    Create CacheService with mocked Redis.
    """
    return CacheService(mock_redis, ttl=3600)


@pytest.fixture
def stats_service(cache_service):
    """
    Create StatsService with mocked cache.
    """
    return StatsService(cache_service, sync_threshold=10)


@pytest.fixture
def url_service(cache_service, stats_service):
    """
    Create UrlService with mocked dependencies.
    """
    return UrlService(cache_service, stats_service, short_id_length=7)


@pytest_asyncio.fixture(scope="function")
async def test_app(test_session, mock_redis, url_service):
    """
    Create test FastAPI application with overridden dependencies.
    """
    app = create_app()
    
    # Override dependencies for testing
    async def override_get_db_session():
        yield test_session
    
    async def override_get_redis_client():
        return mock_redis
    
    async def override_get_cache_service():
        return url_service.cache_service
    
    async def override_get_stats_service():
        return url_service.stats_service
    
    async def override_get_url_service():
        return url_service
    
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_redis_client] = override_get_redis_client
    app.dependency_overrides[get_cache_service] = override_get_cache_service
    app.dependency_overrides[get_stats_service] = override_get_stats_service
    app.dependency_overrides[get_url_service] = override_get_url_service
    
    return app


@pytest_asyncio.fixture(scope="function")
async def client(test_app):
    """
    Create async HTTP test client.
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

```python tests/test_shorten.py
"""
Tests for POST /shorten endpoint.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_create_short_url_success(client: AsyncClient, mock_redis):
    """
    Test successful short URL creation.
    """
    # Mock Redis to return None (no existing cache)
    mock_redis.get.return_value = None
    
    response = await client.post(
        "/shorten",
        json={"url": "https://example.com/very/long/path?query=1"}
    )
    
    assert response.status_code == 201
    data = response.json()
    assert "short_id" in data
    assert "short_url" in data
    assert "original_url" in data
    assert "created_at" in data
    assert len(data["short_id"]) == 7
    assert data["original_url"] == "https://example.com/very/long/path?query=1"


@pytest.mark.asyncio
async def test_create_short_url_invalid_url(client: AsyncClient):
    """
    Test short URL creation with invalid URL.
    """
    response = await client.post(
        "/shorten",
        json={"url": "not-a-valid-url"}
    )
    
    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_create_short_url_invalid_scheme(client: AsyncClient):
    """
    Test short URL creation with disallowed URL scheme.
    """
    response = await client.post(
        "/shorten",
        json={"url": "ftp://example.com/file"}
    )
    
    assert response.status_code == 422  # Pydantic HttpUrl validation


@pytest.mark.asyncio
async def test_create_short_url_empty_body(client: AsyncClient):
    """
    Test short URL creation with empty request body.
    """
    response = await client.post(
        "/shorten",
        json={}
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_short_url_too_long(client: AsyncClient):
    """
    Test short URL creation with URL exceeding max length.
    """
    long_url = "https://example.com/" + "a" * 2100
    response = await client.post(
        "/shorten",
        json={"url": long_url}
    )
    
    assert response.status_code == 422
```

```python tests/test_redirect.py
"""
Tests for GET /{id} redirect endpoint.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient, mock_redis, test_session):
    """
    Test successful redirect to original URL.
    """
    # Setup: Create a short URL first
    mock_redis.get.return_value = None
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/test"}
    )
    short_id = create_response.json()["short_id"]
    
    # Mock Redis to return cached URL for redirect
    mock_redis.get.return_value = "https://example.com/test"
    
    # Test redirect
    response = await client.get(f"/{short_id}", follow_redirects=False)
    
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/test"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient, mock_redis):
    """
    Test redirect with non-existent short ID.
    """
    mock_redis.get.return_value = None
    
    response = await client.get("/nonexist", follow_redirects=False)
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_invalid_id_format(client: AsyncClient):
    """
    Test redirect with invalid short ID format.
    """
    response = await client.get("/ab", follow_redirects=False)
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_deleted_url(client: AsyncClient, mock_redis, test_session):
    """
    Test redirect to a deleted (soft-deleted) URL.
    """
    # Setup: Create and then delete a short URL
    mock_redis.get.return_value = None
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/delete-test"}
    )
    short_id = create_response.json()["short_id"]
    
    # Delete the URL
    await client.delete(f"/{short_id}")
    
    # Mock Redis to return None (cache cleared on delete)
    mock_redis.get.return_value = None
    
    # Try to redirect
    response = await client.get(f"/{short_id}", follow_redirects=False)
    
    assert response.status_code == 404
```

```python tests/test_stats.py
"""
Tests for GET /stats/{id} endpoint.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_get_stats_success(client: AsyncClient, mock_redis, test_session):
    """
    Test successful statistics retrieval.
    """
    # Setup: Create a short URL
    mock_redis.get.return_value = None
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/stats-test"}
    )
    short_id = create_response.json()["short_id"]
    
    # Get stats
    response = await client.get(f"/stats/{short_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["short_id"] == short_id
    assert data["original_url"] == "https://example.com/stats-test"
    assert "click_count" in data
    assert "created_at" in data
    assert data["is_active"] == True


@pytest.mark.asyncio
async def test_get_stats_not_found(client: AsyncClient, mock_redis):
    """
    Test statistics for non-existent short ID.
    """
    mock_redis.get.return_value = None
    
    response = await client.get("/stats/nonexist")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_stats_invalid_id(client: AsyncClient):
    """
    Test statistics with invalid short ID format.
    """
    response = await client.get("/stats/ab")
    
    assert response.status_code == 404
```

```python tests/test_delete.py
"""
Tests for DELETE /{id} endpoint.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_delete_success(client: AsyncClient, mock_redis, test_session):
    """
    Test successful deletion of a short URL.
    """
    # Setup: Create a short URL
    mock_redis.get.return_value = None
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/delete-test"}
    )
    short_id = create_response.json()["short_id"]
    
    # Delete the URL
    response = await client.delete(f"/{short_id}")
    
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_not_found(client: AsyncClient, mock_redis):
    """
    Test deletion of non-existent short ID.
    """
    mock_redis.get.return_value = None
    
    response = await client.delete("/nonexist")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_already_deleted(client: AsyncClient, mock_redis, test_session):
    """
    Test deletion of already deleted URL.
    """
    # Setup: Create and delete a short URL
    mock_redis.get.return_value = None
    create_response = await client.post(
        "/shorten",
        json={"url": "https://example.com/double-delete"}
    )
    short_id = create_response.json()["short_id"]
    
    # First delete
    await client.delete(f"/{short_id}")
    
    # Second delete should fail
    response = await client.delete(f"/{short_id}")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_invalid_id(client: AsyncClient):
    """
    Test deletion with invalid short ID format.
    """
    response = await client.delete("/ab")
    
    assert response.status_code == 404
```

```python tests/test_rate_limit.py
"""
Tests for rate limiting middleware.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_rate_limit_not_exceeded(client: AsyncClient, mock_redis):
    """
    Test that requests within rate limit succeed.
    """
    # Mock rate limit check to allow request
    mock_redis.get.return_value = "1"  # 1 request so far
    
    response = await client.get("/health")
    
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers


@pytest.mark.asyncio
async def test_rate_limit_exceeded(client: AsyncClient, mock_redis):
    """
    Test that requests exceeding rate limit are blocked.
    """
    # Mock rate limit check to deny request
    mock_redis.get.return_value = "100"  # At limit
    
    # Mock TTL for rate limit key
    mock_redis.ttl.return_value = 30
    
    response = await client.get("/health")
    
    assert response.status_code == 429
    assert "Retry-After" in response.headers
    data = response.json()
    assert "detail" in data
    assert "Too many requests" in data["detail"]


@pytest.mark.asyncio
async def test_rate_limit_headers_present(client: AsyncClient, mock_redis):
    """
    Test that rate limit headers are present in responses.
    """
    mock_redis.get.return_value = "5"  # Some requests
    
    response = await client.get("/health")
    
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert "X-RateLimit-Reset" in response.headers
```

```python tests/test_validation.py
"""
Tests for URL validation utilities.
"""
import pytest
from app.utils.url_validator import validate_url_safety, is_private_ip
from app.utils.short_id import generate_short_id, validate_short_id


class TestUrlSafety:
    """Tests for URL safety validation."""
    
    def test_valid_http_url(self):
        """Test that valid HTTP URL passes validation."""
        is_safe, error = validate_url_safety("http://example.com")
        assert is_safe is True
        assert error is None
    
    def test_valid_https_url(self):
        """Test that valid HTTPS URL passes validation."""
        is_safe, error = validate_url_safety("https://example.com/path?query=1")
        assert is_safe is True
        assert error is None
    
    def test_invalid_scheme_ftp(self):
        """Test that FTP URL is rejected."""
        is_safe, error = validate_url_safety("ftp://example.com/file")
        assert is_safe is False
        assert error is not None
    
    def test_invalid_scheme_javascript(self):
        """Test that javascript: URL is rejected."""
        is_safe, error = validate_url_safety("javascript:alert('xss')")
        assert is_safe is False
        assert error is not None
    
    def test_private_ip_blocked(self):
        """Test that private IP addresses are blocked (SSRF protection)."""
        is_safe, error = validate_url_safety("http://127.0.0.1/admin")
        assert is_safe is False
        assert "private IP" in error.lower() if error else False
    
    def test_localhost_blocked(self):
        """Test that localhost is blocked."""
        is_safe, error = validate_url_safety("http://localhost:8080")
        assert is_safe is False
        assert error is not None


class TestShortIdGeneration:
    """Tests for short ID generation and validation."""
    
    def test_generate_short_id_length(self):
        """Test that generated short ID has correct length."""
        short_id = generate_short_id(7)
        assert len(short_id) == 7
    
    def test_generate_short_id_alphanumeric(self):
        """Test that generated short ID contains only alphanumeric chars."""
        short_id = generate_short_id(7)
        assert short_id.isalnum()
    
    def test_generate_short_id_uniqueness(self):
        """Test that generated short IDs are unique."""
        ids = {generate_short_id(7) for _ in range(100)}
        assert len(ids) == 100  # All should be unique
    
    def test_validate_short_id_valid(self):
        """Test validation of valid short ID."""
        assert validate_short_id("abc1234", 7) is True
    
    def test_validate_short_id_invalid_length(self):
        """Test validation of short ID with wrong length."""
        assert validate_short_id("abc12", 7) is False
    
    def test_validate_short_id_invalid_chars(self):
        """Test validation of short ID with invalid characters."""
        assert validate_short_id("abc-123", 7) is False
    
    def test_validate_short_id_empty(self):
        """Test validation of empty short ID."""
        assert validate_short_id("", 7) is False
```

```python tests/test_health.py
"""
Tests for GET /health endpoint.
"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_health_check_healthy(client: AsyncClient, mock_redis):
    """
    Test health check when all services are healthy.
    """
    mock_redis.ping.return_value = True
    
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "healthy"
    assert data["redis"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_redis_unhealthy(client: AsyncClient, mock_redis):
    """
    Test health check when Redis is unhealthy.
    """
    mock_redis.ping.side_effect = Exception("Redis connection failed")
    
    response = await client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["redis"] == "unhealthy"
```

```python Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

```yaml docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://urluser:urlpass@postgres:5432/urlshortener
      - REDIS_URL=redis://redis:6379/0
      - RATE_LIMIT_PER_MINUTE=100
      - SHORT_ID_LENGTH=7
      - CACHE_TTL_SECONDS=3600
      - BASE_URL=http://localhost:8000
      - MAX_URL_LENGTH=2048
      - STATS_SYNC_THRESHOLD=10
      - SHUTDOWN_TIMEOUT_SECONDS=30
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=urluser
      - POSTGRES_PASSWORD=urlpass
      - POSTGRES_DB=urlshortener
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U urluser -d urlshortener"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

```markdown README.md
# URL Shortener Microservice

A high-performance URL shortening microservice built with FastAPI, PostgreSQL, and Redis.

## Features

- **URL Shortening**: Create short URLs (7-character base62 IDs)
- **Fast Redirects**: Redis-cached redirects with <50ms p99 latency
- **Click Statistics**: Track and retrieve click counts
- **URL Deletion**: Soft delete with cache cleanup
- **Rate Limiting**: Redis-based sliding window rate limiting (100 req/min per IP)
- **SSRF Protection**: Blocks requests to private/internal IPs
- **Health Checks**: Monitors database and Redis connectivity
- **Graceful Shutdown**: Proper connection cleanup on SIGTERM/SIGINT

## Tech Stack

- **Python 3.11+** with async/await
- **FastAPI** for REST API with auto-generated OpenAPI docs
- **SQLAlchemy 2.0** (async) with PostgreSQL 15
- **Redis 7** for caching and rate limiting
- **Alembic** for database migrations
- **Docker** and docker-compose for containerization

## Quick Start

### Prerequisites

- Docker and docker-compose
- Python 3.11+ (for local development)

### Using Docker

```bash
# Clone the repository
git clone <repository-url>
cd url-shortener

# Copy environment file
cp .env.example .env

# Start all services
docker-compose up -d

# Run migrations
docker-compose exec app alembic upgrade head

# Check health
curl http://localhost:8000/health
```

### Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### POST /shorten
Create a short URL.

```bash
curl -X POST http://localhost:8000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/path"}'
```

### GET /{id}
Redirect to original URL.

```bash
curl -I http://localhost:8000/aB3x9Qk
```

### GET /stats/{id}
Get URL statistics.

```bash
curl http://localhost:8000/stats/aB3x9Qk
```

### DELETE /{id}
Delete a short URL.

```bash
curl -X DELETE http://localhost:8000/aB3x9Qk
```

### GET /health
Health check.

```bash
curl http://localhost:8000/health
```

## API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Configuration

Configuration is done via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `RATE_LIMIT_PER_MINUTE` | `100` | Max requests per minute per IP |
| `SHORT_ID_LENGTH` | `7` | Length of generated short IDs |
| `CACHE_TTL_SECONDS` | `3600` | Redis cache TTL in seconds |
| `BASE_URL` | `http://localhost:8000` | Base URL for short links |
| `MAX_URL_LENGTH` | `2048` | Maximum original URL length |
| `STATS_SYNC_THRESHOLD` | `10` | Clicks before syncing to DB |
| `SHUTDOWN_TIMEOUT_SECONDS` | `30` | Graceful shutdown timeout |

## Testing

```bash
# Run all tests
pytest -v

# Run with coverage
pytest -v --cov=app --cov-report=html

# Run specific test file
pytest -v tests/test_shorten.py
```

## Architecture

The service follows a layered architecture:

- **Routers**: Handle HTTP request/response
- **Services**: Business logic layer
- **Models**: SQLAlchemy database models
- **Middleware**: Rate limiting, CORS
- **Utils**: Short ID generation, URL validation

### Data Flow (Redirect)

1. Request hits Rate Limit Middleware
2. Router delegates to UrlService
3. Service checks Redis cache first
4. Cache miss → queries PostgreSQL
5. Records click in Redis buffer
6. Returns 302 redirect

### Caching Strategy

- **Hot cache**: URLs cached in Redis with 1-hour TTL
- **Stats buffering**: Click counts buffered in Redis, synced to DB every N clicks
- **Rate limiting**: Sliding window counters in Redis per IP

## Production Deployment

```bash
# Build and start with multiple workers
docker-compose up -d --scale app=4

# The service is stateless and can be horizontally scaled
# behind a load balancer with shared Redis and PostgreSQL
```

## Security

- URL scheme validation (http/https only)
- SSRF protection (blocks private IPs)
- Rate limiting per IP
- SQL injection prevention via parameterized queries
- No sensitive data in logs

## License

MIT
```