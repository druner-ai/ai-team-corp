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
# Core
fastapi==0.110.0
uvicorn[standard]==0.27.1
pydantic==2.6.1
pydantic-settings==2.1.0

# Database
sqlalchemy[asyncio]==2.0.27
asyncpg==0.29.0
alembic==1.13.1

# Cache
redis==5.0.1

# Rate Limiting
slowapi==0.1.9

# Logging
structlog==24.1.0

# Testing
pytest==8.0.1
pytest-asyncio==0.23.4
httpx==0.27.0
pytest-cov==4.1.0
testcontainers==4.0.0

# Utils
python-dotenv==1.0.1
```

```python .env.example
# Database
DATABASE_URL=postgresql+asyncpg://shortener:shortener_pass@localhost:5432/shortener_db

# Redis
REDIS_URL=redis://localhost:6379/0

# Application
SHORT_CODE_LENGTH=6
CACHE_TTL_SECONDS=86400
BASE_URL=http://localhost:8000

# Rate Limiting
RATE_LIMIT_SHORTEN=30/minute
RATE_LIMIT_DEFAULT=100/minute

# Security
BLOCK_PRIVATE_IPS=true
ALLOWED_ORIGINS=

# Logging
LOG_LEVEL=INFO
```

```python app/__init__.py
"""
URL Shortener Microservice
"""

__version__ = "1.0.0"
```

```python app/config.py
"""
Application configuration using Pydantic Settings.
All settings are loaded from environment variables with sensible defaults.
"""

from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database
    database_url: str = "postgresql+asyncpg://shortener:shortener_pass@localhost:5432/shortener_db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Application
    short_code_length: int = 6
    cache_ttl_seconds: int = 86400  # 24 hours
    base_url: str = "http://localhost:8000"

    # Rate Limiting
    rate_limit_shorten: str = "30/minute"
    rate_limit_default: str = "100/minute"

    # Security
    block_private_ips: bool = True
    allowed_origins: str = ""

    # Logging
    log_level: str = "INFO"

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated origins into a list."""
        if not self.allowed_origins:
            return []
        return [origin.strip() for origin in self.allowed_origins.split(",")]


settings = Settings()
```

```python app/core/__init__.py
"""
Core utilities: security, exceptions, rate limiting.
"""
```

```python app/core/exceptions.py
"""
Custom exceptions and exception handlers for the URL Shortener service.
"""

from typing import Any
from fastapi import Request
from fastapi.responses import JSONResponse


class URLShortenerException(Exception):
    """Base exception for URL Shortener service."""

    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class URLNotFoundException(URLShortenerException):
    """Raised when a short code is not found."""

    def __init__(self, short_code: str):
        super().__init__(
            message=f"URL with short code '{short_code}' not found",
            status_code=404,
        )


class URLAlreadyDeletedException(URLShortenerException):
    """Raised when attempting to delete an already deleted URL."""

    def __init__(self, short_code: str):
        super().__init__(
            message=f"URL with short code '{short_code}' is already deleted",
            status_code=409,
        )


class URLExpiredException(URLShortenerException):
    """Raised when a URL has expired."""

    def __init__(self, short_code: str):
        super().__init__(
            message=f"URL with short code '{short_code}' has expired",
            status_code=410,
        )


class URLAlreadyExistsException(URLShortenerException):
    """Raised when a URL already has a short code."""

    def __init__(self, short_code: str, original_url: str):
        self.short_code = short_code
        self.original_url = original_url
        super().__init__(
            message=f"URL already shortened with code '{short_code}'",
            status_code=409,
        )


class InvalidURLException(URLShortenerException):
    """Raised when the provided URL is invalid."""

    def __init__(self, url: str, reason: str = ""):
        detail = f"Invalid URL: {url}"
        if reason:
            detail += f" - {reason}"
        super().__init__(message=detail, status_code=400)


class ServiceUnavailableException(URLShortenerException):
    """Raised when a required service (DB, Redis) is unavailable."""

    def __init__(self, service: str):
        super().__init__(
            message=f"Service unavailable: {service} is not accessible",
            status_code=503,
        )


async def url_shortener_exception_handler(
    request: Request, exc: URLShortenerException
) -> JSONResponse:
    """Global exception handler for URLShortenerException."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )


async def generic_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Global exception handler for unhandled exceptions."""
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
```

```python app/core/security.py
"""
Security utilities: URL validation and SSRF protection.
"""

import ipaddress
import socket
from urllib.parse import urlparse

from app.config import settings


# Private IP ranges to block (SSRF protection)
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("0.0.0.0/8"),
]

# Blocked hostnames
BLOCKED_HOSTNAMES = {"localhost", "0.0.0.0"}


def is_private_ip(hostname: str) -> bool:
    """
    Check if a hostname resolves to a private IP address.

    Args:
        hostname: The hostname to check.

    Returns:
        True if the hostname resolves to a private IP, False otherwise.
    """
    if not settings.block_private_ips:
        return False

    # Check if hostname is in blocked list
    if hostname.lower() in BLOCKED_HOSTNAMES:
        return True

    try:
        # Try to parse as IP address first
        ip = ipaddress.ip_address(hostname)
        return any(ip in network for network in PRIVATE_IP_RANGES)
    except ValueError:
        # Not an IP address, try DNS resolution
        try:
            resolved_ip = socket.gethostbyname(hostname)
            ip = ipaddress.ip_address(resolved_ip)
            return any(ip in network for network in PRIVATE_IP_RANGES)
        except (socket.gaierror, ValueError):
            # If we can't resolve, assume it's safe
            # Note: This could be a potential bypass, but blocking unresolvable
            # hosts would break legitimate use cases
            return False


def validate_url(url: str) -> str:
    """
    Validate a URL for safety and correctness.

    Checks:
    - Scheme is http or https
    - URL has a valid netloc (domain)
    - URL length is within limits (2048 chars)
    - Host does not resolve to private IP (if BLOCK_PRIVATE_IPS is enabled)

    Args:
        url: The URL to validate.

    Returns:
        The validated URL string.

    Raises:
        InvalidURLException: If the URL fails validation.
    """
    from app.core.exceptions import InvalidURLException

    # Check length
    if len(url) > 2048:
        raise InvalidURLException(url, "URL exceeds maximum length of 2048 characters")

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception:
        raise InvalidURLException(url, "Could not parse URL")

    # Check scheme
    if parsed.scheme not in ("http", "https"):
        raise InvalidURLException(url, "Only http and https schemes are allowed")

    # Check netloc (domain)
    if not parsed.netloc:
        raise InvalidURLException(url, "URL must have a valid domain")

    # Extract hostname (remove port if present)
    hostname = parsed.hostname
    if not hostname:
        raise InvalidURLException(url, "Could not extract hostname from URL")

    # Check for private IPs
    if is_private_ip(hostname):
        raise InvalidURLException(url, "URL resolves to a private/internal IP address")

    return url
```

```python app/core/rate_limiter.py
"""
Rate limiting configuration using slowapi with Redis backend.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.middleware import SlowAPIMiddleware
from fastapi import FastAPI

from app.config import settings


def create_limiter() -> Limiter:
    """
    Create and configure the rate limiter.

    Returns:
        Configured Limiter instance with Redis storage.
    """
    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri=settings.redis_url,
        default_limits=[settings.rate_limit_default],
    )
    return limiter


def setup_rate_limiting(app: FastAPI, limiter: Limiter) -> None:
    """
    Set up rate limiting middleware and exception handlers.

    Args:
        app: FastAPI application instance.
        limiter: Configured Limiter instance.
    """
    app.state.limiter = limiter
    app.add_middleware(SlowAPIMiddleware)
```

```python app/db/__init__.py
"""
Database and Redis connection management.
"""
```

```python app/db/session.py
"""
Async SQLAlchemy engine and session management.
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import settings

# Create async engine with connection pooling
# pool_size=20, max_overflow=10 as per architecture document
engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before using
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncSession:
    """
    Dependency that provides an async database session.

    Yields:
        AsyncSession: SQLAlchemy async session.

    Note:
        Session is automatically closed when the request is complete.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
```

```python app/db/redis_client.py
"""
Redis connection pool and client management.
"""

import redis.asyncio as aioredis
from typing import Optional

from app.config import settings

# Global Redis connection pool
_redis_pool: Optional[aioredis.ConnectionPool] = None
_redis_client: Optional[aioredis.Redis] = None


async def get_redis_pool() -> aioredis.ConnectionPool:
    """
    Get or create the Redis connection pool.

    Returns:
        aioredis.ConnectionPool: The Redis connection pool.
    """
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(
            settings.redis_url,
            max_connections=50,
            decode_responses=True,
        )
    return _redis_pool


async def get_redis() -> aioredis.Redis:
    """
    Dependency that provides a Redis client.

    Returns:
        aioredis.Redis: Redis client instance.

    Note:
        Uses a connection pool for efficiency.
    """
    pool = await get_redis_pool()
    return aioredis.Redis(connection_pool=pool)


async def close_redis_pool() -> None:
    """Close the Redis connection pool gracefully."""
    global _redis_pool, _redis_client
    if _redis_pool:
        await _redis_pool.disconnect()
        _redis_pool = None
        _redis_client = None
```

```python app/models/__init__.py
"""
SQLAlchemy ORM models.
"""
```

```python app/models/url.py
"""
SQLAlchemy model for the urls table.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class Url(Base):
    """
    URL model representing shortened URLs.

    Attributes:
        id: Internal auto-incrementing ID.
        short_code: Unique short code (base62, 6 chars).
        original_url: The original long URL.
        created_at: Timestamp of creation.
        is_deleted: Soft delete flag.
        expires_at: Optional expiration timestamp.
    """

    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    short_code: Mapped[str] = mapped_column(
        String(10), unique=True, nullable=False, index=True
    )
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    # Additional indexes as per architecture document
    __table_args__ = (
        Index("idx_urls_short_code", "short_code", unique=True),
        Index("idx_urls_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Url(id={self.id}, short_code='{self.short_code}')>"
```

```python app/repositories/__init__.py
"""
Repository layer for database operations.
"""
```

```python app/repositories/url_repository.py
"""
Repository for URL CRUD operations.
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import Url


class UrlRepository:
    """
    Repository for URL database operations.

    Provides async methods for CRUD operations on the urls table.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        short_code: str,
        original_url: str,
        expires_at: Optional[datetime] = None,
    ) -> Url:
        """
        Create a new shortened URL record.

        Args:
            short_code: The generated short code.
            original_url: The original long URL.
            expires_at: Optional expiration datetime.

        Returns:
            The created Url instance.
        """
        url = Url(
            short_code=short_code,
            original_url=original_url,
            expires_at=expires_at,
        )
        self.session.add(url)
        await self.session.commit()
        await self.session.refresh(url)
        return url

    async def get_by_short_code(self, short_code: str) -> Optional[Url]:
        """
        Retrieve a URL by its short code.

        Args:
            short_code: The short code to look up.

        Returns:
            Url instance if found, None otherwise.
        """
        result = await self.session.execute(
            select(Url).where(Url.short_code == short_code)
        )
        return result.scalar_one_or_none()

    async def get_active_by_short_code(self, short_code: str) -> Optional[Url]:
        """
        Retrieve an active (not deleted, not expired) URL by short code.

        Args:
            short_code: The short code to look up.

        Returns:
            Url instance if found and active, None otherwise.
        """
        result = await self.session.execute(
            select(Url).where(
                Url.short_code == short_code,
                Url.is_deleted == False,
                (Url.expires_at.is_(None)) | (Url.expires_at > datetime.now(timezone.utc)),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_original_url(self, original_url: str) -> Optional[Url]:
        """
        Find an existing URL by its original URL.

        Args:
            original_url: The original URL to search for.

        Returns:
            Url instance if found, None otherwise.
        """
        result = await self.session.execute(
            select(Url).where(
                Url.original_url == original_url,
                Url.is_deleted == False,
            )
        )
        return result.scalar_one_or_none()

    async def soft_delete(self, short_code: str) -> Optional[Url]:
        """
        Soft delete a URL by marking it as deleted.

        Args:
            short_code: The short code to delete.

        Returns:
            Updated Url instance if found, None otherwise.
        """
        url = await self.get_by_short_code(short_code)
        if url is None:
            return None

        url.is_deleted = True
        await self.session.commit()
        await self.session.refresh(url)
        return url

    async def increment_clicks(self, short_code: str) -> None:
        """
        Increment click counter for a URL.
        
        Note: This is a placeholder. Actual click counting is done in Redis.
        This method exists for potential future use or batch sync operations.

        Args:
            short_code: The short code to increment clicks for.
        """
        # Click counting is primarily handled in Redis via cache_service
        # This method is reserved for batch synchronization from Redis to PostgreSQL
        pass
```

```python app/schemas/__init__.py
"""
Pydantic schemas for request/response validation.
"""
```

```python app/schemas/shorten.py
"""
Schemas for the URL shortening endpoint.
"""

from pydantic import BaseModel, Field, field_validator
from app.core.security import validate_url


class ShortenRequest(BaseModel):
    """
    Request schema for POST /shorten endpoint.

    Attributes:
        url: The long URL to shorten. Must be valid http/https URL.
    """

    url: str = Field(
        ...,
        description="The long URL to shorten",
        max_length=2048,
        examples=["https://example.com/very/long/path?query=1"],
    )

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        """
        Validate the URL field using security module.

        Args:
            v: The URL string to validate.

        Returns:
            Validated URL string.

        Raises:
            InvalidURLException: If URL is invalid.
        """
        return validate_url(v)


class ShortenResponse(BaseModel):
    """
    Response schema for POST /shorten endpoint.

    Attributes:
        short_code: The generated short code.
        short_url: The full short URL.
        original_url: The original long URL.
    """

    short_code: str = Field(..., description="The generated short code")
    short_url: str = Field(..., description="The full short URL")
    original_url: str = Field(..., description="The original long URL")

    model_config = {
        "json_schema_extra": {
            "example": {
                "short_code": "aB3x9Q",
                "short_url": "http://localhost:8000/aB3x9Q",
                "original_url": "https://example.com/very/long/path?query=1",
            }
        }
    }
```

```python app/schemas/stats.py
"""
Schemas for the statistics endpoint.
"""

from datetime import datetime
from pydantic import BaseModel, Field


class StatsResponse(BaseModel):
    """
    Response schema for GET /stats/{short_code} endpoint.

    Attributes:
        short_code: The short code.
        original_url: The original long URL.
        clicks: Number of clicks/redirects.
        created_at: Creation timestamp.
    """

    short_code: str = Field(..., description="The short code")
    original_url: str = Field(..., description="The original long URL")
    clicks: int = Field(..., description="Number of clicks", ge=0)
    created_at: datetime = Field(..., description="Creation timestamp")

    model_config = {
        "json_schema_extra": {
            "example": {
                "short_code": "aB3x9Q",
                "original_url": "https://example.com/very/long/path?query=1",
                "clicks": 42,
                "created_at": "2025-01-15T10:30:00Z",
            }
        }
    }
```

```python app/utils/__init__.py
"""
Utility modules.
"""
```

```python app/utils/base62.py
"""
Base62 encoding/decoding utilities.

Base62 uses characters: 0-9, a-z, A-Z (62 characters total).
This is used for generating short codes from integer IDs.
"""

import string

# Base62 alphabet
BASE62_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
BASE62_BASE = len(BASE62_ALPHABET)  # 62

# Character to index mapping for decoding
_BASE62_CHAR_TO_INDEX = {char: idx for idx, char in enumerate(BASE62_ALPHABET)}


def encode_base62(number: int) -> str:
    """
    Encode an integer to a base62 string.

    Args:
        number: Non-negative integer to encode.

    Returns:
        Base62 encoded string.

    Raises:
        ValueError: If number is negative.

    Examples:
        >>> encode_base62(0)
        '0'
        >>> encode_base62(61)
        'Z'
        >>> encode_base62(62)
        '10'
    """
    if number < 0:
        raise ValueError("Number must be non-negative")

    if number == 0:
        return BASE62_ALPHABET[0]

    result = []
    while number > 0:
        number, remainder = divmod(number, BASE62_BASE)
        result.append(BASE62_ALPHABET[remainder])

    return "".join(reversed(result))


def decode_base62(encoded: str) -> int:
    """
    Decode a base62 string back to an integer.

    Args:
        encoded: Base62 encoded string.

    Returns:
        Decoded integer.

    Raises:
        ValueError: If string contains invalid characters.

    Examples:
        >>> decode_base62('0')
        0
        >>> decode_base62('Z')
        61
        >>> decode_base62('10')
        62
    """
    if not encoded:
        raise ValueError("Encoded string must not be empty")

    result = 0
    for char in encoded:
        if char not in _BASE62_CHAR_TO_INDEX:
            raise ValueError(f"Invalid base62 character: '{char}'")
        result = result * BASE62_BASE + _BASE62_CHAR_TO_INDEX[char]

    return result
```

```python app/services/__init__.py
"""
Service layer containing business logic.
"""
```

```python app/services/code_generator.py
"""
Short code generation service.

Generates unique short codes using base62 encoding of a sequence number
with collision retry logic.
"""

import secrets
from typing import Optional

from app.config import settings
from app.utils.base62 import encode_base62


class CodeGenerator:
    """
    Generates unique short codes for URLs.

    Uses a combination of base62 encoding and random suffix for uniqueness.
    Implements retry logic for collision handling (max 3 attempts as per spec).
    """

    MAX_RETRIES = 3

    def __init__(self, code_length: Optional[int] = None):
        """
        Initialize the code generator.

        Args:
            code_length: Length of generated codes. Defaults to settings.short_code_length.
        """
        self.code_length = code_length or settings.short_code_length

    def generate(self, sequence_number: int) -> str:
        """
        Generate a short code from a sequence number.

        The code is generated by base62-encoding the sequence number and
        padding/truncating to the desired length. If the encoded value is
        shorter than required, random characters are appended.

        Args:
            sequence_number: A unique sequence number (e.g., from DB sequence).

        Returns:
            A short code string of length self.code_length.
        """
        # Encode the sequence number to base62
        encoded = encode_base62(sequence_number)

        # If encoded is shorter than desired length, pad with random chars
        if len(encoded) < self.code_length:
            padding_length = self.code_length - len(encoded)
            random_suffix = self._generate_random_suffix(padding_length)
            return encoded + random_suffix

        # If encoded is longer, truncate (shouldn't happen with proper sequence management)
        return encoded[: self.code_length]

    def generate_with_retry(
        self, sequence_number: int, is_code_taken: callable
    ) -> str:
        """
        Generate a short code with collision retry logic.

        Attempts to generate a unique code up to MAX_RETRIES times.
        On collision, modifies the sequence number and tries again.

        Args:
            sequence_number: Base sequence number.
            is_code_taken: Async callable that checks if a code already exists.

        Returns:
            A unique short code.

        Raises:
            RuntimeError: If unable to generate unique code after max retries.
        """
        import asyncio

        for attempt in range(self.MAX_RETRIES):
            # Add attempt offset to sequence for retry variation
            adjusted_sequence = sequence_number + (attempt * 1000)
            code = self.generate(adjusted_sequence)

            # Check if code is already taken
            if not is_code_taken(code):
                return code

        raise RuntimeError(
            f"Failed to generate unique short code after {self.MAX_RETRIES} attempts"
        )

    def _generate_random_suffix(self, length: int) -> str:
        """
        Generate a random base62 suffix of given length.

        Args:
            length: Number of random characters to generate.

        Returns:
            Random base62 string.
        """
        from app.utils.base62 import BASE62_ALPHABET

        return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))
```

```python app/services/cache_service.py
"""
Redis cache service for URL caching and click counting.

Provides:
- URL caching with TTL (24 hours)
- Click counting via Redis Hash
- Cache invalidation
- Graceful degradation when Redis is unavailable
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """
    Service for Redis cache operations.

    Handles caching of URL mappings and click statistics.
    Implements circuit breaker pattern for Redis unavailability.
    """

    # Redis key patterns
    URL_KEY_PREFIX = "url:"
    STATS_KEY_PREFIX = "stats:"

    def __init__(self, redis_client: aioredis.Redis):
        """
        Initialize the cache service.

        Args:
            redis_client: Async Redis client instance.
        """
        self.redis = redis_client
        self._circuit_open = False
        self._failure_count = 0
        self._failure_threshold = 3
        self._timeout = 1.0  # 1 second timeout as per spec

    async def _execute_with_fallback(self, operation, fallback_value=None):
        """
        Execute a Redis operation with circuit breaker and fallback.

        Args:
            operation: Async callable that performs the Redis operation.
            fallback_value: Value to return if Redis is unavailable.

        Returns:
            Result of operation or fallback_value.
        """
        if self._circuit_open:
            return fallback_value

        try:
            result = await asyncio.wait_for(operation(), timeout=self._timeout)
            self._failure_count = 0
            return result
        except (asyncio.TimeoutError, Exception) as e:
            self._failure_count += 1
            logger.warning(f"Redis operation failed: {e}")

            if self._failure_count >= self._failure_threshold:
                self._circuit_open = True
                logger.error("Circuit breaker opened for Redis")

            return fallback_value

    async def cache_url(self, short_code: str, original_url: str) -> bool:
        """
        Cache a URL mapping in Redis with TTL.

        Args:
            short_code: The short code.
            original_url: The original URL.

        Returns:
            True if cached successfully, False otherwise.
        """
        key = f"{self.URL_KEY_PREFIX}{short_code}"

        async def _set():
            await self.redis.setex(key, settings.cache_ttl_seconds, original_url)
            return True

        result = await self._execute_with_fallback(_set, fallback_value=False)
        return result is True

    async def get_cached_url(self, short_code: str) -> Optional[str]:
        """
        Retrieve a cached URL by short code.

        Args:
            short_code: The short code to look up.

        Returns:
            Original URL if cached, None otherwise.
        """
        key = f"{self.URL_KEY_PREFIX}{short_code}"

        async def _get():
            return await self.redis.get(key)

        return await self._execute_with_fallback(_get)

    async def invalidate_cache(self, short_code: str) -> bool:
        """
        Remove a URL from cache.

        Args:
            short_code: The short code to invalidate.

        Returns:
            True if invalidated, False otherwise.
        """
        key = f"{self.URL_KEY_PREFIX}{short_code}"

        async def _delete():
            await self.redis.delete(key)
            return True

        result = await self._execute_with_fallback(_delete, fallback_value=False)
        return result is True

    async def increment_clicks(self, short_code: str) -> int:
        """
        Increment the click counter for a short code.

        Uses Redis HINCRBY for atomic increment.

        Args:
            short_code: The short code.

        Returns:
            New click count, or -1 if Redis is unavailable.
        """
        stats_key = f"{self.STATS_KEY_PREFIX}{short_code}"

        async def _increment():
            pipe = self.redis.pipeline()
            pipe.hincrby(stats_key, "clicks", 1)
            pipe.hset(
                stats_key,
                "last_accessed",
                datetime.now(timezone.utc).isoformat(),
            )
            results = await pipe.execute()
            return int(results[0])

        result = await self._execute_with_fallback(_increment, fallback_value=-1)
        return result if result != -1 else -1

    async def get_stats(self, short_code: str) -> dict:
        """
        Get click statistics for a short code.

        Args:
            short_code: The short code.

        Returns:
            Dict with 'clicks' and 'last_accessed', or empty dict if unavailable.
        """
        stats_key = f"{self.STATS_KEY_PREFIX}{short_code}"

        async def _get():
            return await self.redis.hgetall(stats_key)

        result = await self._execute_with_fallback(_get, fallback_value={})
        return result if result else {}

    async def is_healthy(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if Redis is responsive, False otherwise.
        """
        try:
            await asyncio.wait_for(self.redis.ping(), timeout=self._timeout)
            return True
        except Exception:
            return False
```

```python app/services/url_service.py
"""
URL shortening business logic service.

Orchestrates the URL shortening workflow:
- URL validation
- Duplicate checking
- Short code generation
- Persistence and caching
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.exceptions import (
    URLAlreadyDeletedException,
    URLAlreadyExistsException,
    URLExpiredException,
    URLNotFoundException,
)
from app.models.url import Url
from app.repositories.url_repository import UrlRepository
from app.services.cache_service import CacheService
from app.services.code_generator import CodeGenerator

logger = logging.getLogger(__name__)


class UrlService:
    """
    Service for URL shortening operations.

    Coordinates between repository, cache, and code generator
    to implement the business logic.
    """

    def __init__(
        self,
        repository: UrlRepository,
        cache_service: CacheService,
        code_generator: CodeGenerator,
    ):
        """
        Initialize the URL service.

        Args:
            repository: URL repository for database operations.
            cache_service: Cache service for Redis operations.
            code_generator: Code generator for creating short codes.
        """
        self.repository = repository
        self.cache = cache_service
        self.generator = code_generator

    async def shorten_url(self, original_url: str) -> dict:
        """
        Shorten a URL.

        Workflow:
        1. Check if URL already has a short code
        2. If yes, return existing code (409 Conflict)
        3. Generate new unique short code
        4. Save to database
        5. Cache in Redis
        6. Return response data

        Args:
            original_url: The validated original URL.

        Returns:
            Dict with short_code, short_url, original_url.

        Raises:
            URLAlreadyExistsException: If URL already shortened.
        """
        # Check for existing URL
        existing = await self.repository.get_by_original_url(original_url)
        if existing:
            raise URLAlreadyExistsException(
                short_code=existing.short_code,
                original_url=original_url,
            )

        # Generate unique short code
        # Use a simple incrementing counter based on current timestamp
        # In production, this should use a database sequence
        import time
        sequence_number = int(time.time() * 1000) % (10**10)

        def is_code_taken(code: str) -> bool:
            """Synchronous check for code availability."""
            # We'll check asynchronously in the actual flow
            return False

        short_code = self.generator.generate(sequence_number)

        # Verify uniqueness in database (with retry)
        for attempt in range(self.generator.MAX_RETRIES):
            existing_code = await self.repository.get_by_short_code(short_code)
            if not existing_code:
                break
            # Collision detected, generate new code
            sequence_number += 1000
            short_code = self.generator.generate(sequence_number)
        else:
            raise RuntimeError("Failed to generate unique short code")

        # Save to database
        url = await self.repository.create(
            short_code=short_code,
            original_url=original_url,
        )

        # Cache in Redis (fire and forget - don't block on cache failure)
        await self.cache.cache_url(short_code, original_url)

        # Build response
        short_url = f"{settings.base_url}/{short_code}"
        return {
            "short_code": short_code,
            "short_url": short_url,
            "original_url": original_url,
        }

    async def get_original_url(self, short_code: str) -> str:
        """
        Get the original URL for a short code and increment click counter.

        Workflow:
        1. Try Redis cache first
        2. On cache miss, query database
        3. Check if URL is deleted or expired
        4. Cache the result in Redis
        5. Increment click counter
        6. Return original URL

        Args:
            short_code: The short code to resolve.

        Returns:
            The original URL string.

        Raises:
            URLNotFoundException: If short code not found.
            URLAlreadyDeletedException: If URL is soft-deleted.
            URLExpiredException: If URL has expired.
        """
        # Try cache first
        cached_url = await self.cache.get_cached_url(short_code)
        if cached_url:
            # Increment click counter asynchronously
            await self.cache.increment_clicks(short_code)
            return cached_url

        # Cache miss - query database
        url = await self.repository.get_by_short_code(short_code)

        if url is None:
            raise URLNotFoundException(short_code)

        if url.is_deleted:
            raise URLAlreadyDeletedException(short_code)

        if url.expires_at and url.expires_at < datetime.now(timezone.utc):
            raise URLExpiredException(short_code)

        # Cache for future requests
        await self.cache.cache_url(short_code, url.original_url)

        # Increment click counter
        await self.cache.increment_clicks(short_code)

        return url.original_url

    async def get_stats(self, short_code: str) -> dict:
        """
        Get statistics for a short code.

        Combines data from database (original_url, created_at)
        and Redis (click count).

        Args:
            short_code: The short code.

        Returns:
            Dict with short_code, original_url, clicks, created_at.

        Raises:
            URLNotFoundException: If short code not found.
        """
        url = await self.repository.get_by_short_code(short_code)

        if url is None or url.is_deleted:
            raise URLNotFoundException(short_code)

        # Get click count from Redis
        redis_stats = await self.cache.get_stats(short_code)
        clicks = int(redis_stats.get("clicks", 0))

        return {
            "short_code": url.short_code,
            "original_url": url.original_url,
            "clicks": clicks,
            "created_at": url.created_at,
        }

    async def delete_url(self, short_code: str) -> None:
        """
        Soft delete a URL.

        Workflow:
        1. Check if URL exists
        2. Check if already deleted
        3. Soft delete in database
        4. Invalidate cache

        Args:
            short_code: The short code to delete.

        Raises:
            URLNotFoundException: If short code not found.
            URLAlreadyDeletedException: If already deleted.
        """
        url = await self.repository.get_by_short_code(short_code)

        if url is None:
            raise URLNotFoundException(short_code)

        if url.is_deleted:
            raise URLAlreadyDeletedException(short_code)

        # Soft delete
        await self.repository.soft_delete(short_code)

        # Invalidate cache
        await self.cache.invalidate_cache(short_code)
```

```python app/api/__init__.py
"""
API layer - routers and dependencies.
"""
```

```python app/api/deps.py
"""
Dependency injection for FastAPI routes.

Provides:
- Database session
- Redis client
- Service instances
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from app.db.session import get_db
from app.db.redis_client import get_redis
from app.repositories.url_repository import UrlRepository
from app.services.cache_service import CacheService
from app.services.code_generator import CodeGenerator
from app.services.url_service import UrlService


async def get_repository(
    session: AsyncSession = Depends(get_db),
) -> UrlRepository:
    """
    Dependency that provides a UrlRepository instance.

    Args:
        session: Async database session.

    Returns:
        UrlRepository instance.
    """
    return UrlRepository(session)


async def get_cache_service(
    redis: aioredis.Redis = Depends(get_redis),
) -> CacheService:
    """
    Dependency that provides a CacheService instance.

    Args:
        redis: Async Redis client.

    Returns:
        CacheService instance.
    """
    return CacheService(redis)


async def get_code_generator() -> CodeGenerator:
    """
    Dependency that provides a CodeGenerator instance.

    Returns:
        CodeGenerator instance.
    """
    return CodeGenerator()


async def get_url_service(
    repository: UrlRepository = Depends(get_repository),
    cache_service: CacheService = Depends(get_cache_service),
    code_generator: CodeGenerator = Depends(get_code_generator),
) -> UrlService:
    """
    Dependency that provides a fully initialized UrlService.

    Args:
        repository: URL repository.
        cache_service: Cache service.
        code_generator: Code generator.

    Returns:
        UrlService instance.
    """
    return UrlService(
        repository=repository,
        cache_service=cache_service,
        code_generator=code_generator,
    )
```

```python app/api/v1/__init__.py
"""
API v1 package.
"""
```

```python app/api/v1/router.py
"""
Main v1 API router that includes all endpoint routers.
"""

from fastapi import APIRouter

from app.api.v1.shorten import router as shorten_router
from app.api.v1.redirect import router as redirect_router
from app.api.v1.stats import router as stats_router
from app.api.v1.delete import router as delete_router

# Create main v1 router
router = APIRouter(prefix="/v1")

# Include sub-routers
router.include_router(shorten_router, tags=["Shorten"])
router.include_router(redirect_router, tags=["Redirect"])
router.include_router(stats_router, tags=["Stats"])
router.include_router(delete_router, tags=["Delete"])
```

```python app/api/v1/shorten.py
"""
POST /shorten endpoint for URL shortening.
"""

import logging

from fastapi import APIRouter, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_url_service
from app.config import settings
from app.core.exceptions import URLAlreadyExistsException
from app.schemas.shorten import ShortenRequest, ShortenResponse
from app.services.url_service import UrlService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/shorten",
    response_model=ShortenResponse,
    status_code=201,
    summary="Shorten a URL",
    description="Create a shortened URL from a long URL.",
    responses={
        201: {"description": "URL successfully shortened"},
        400: {"description": "Invalid URL provided"},
        409: {"description": "URL already shortened"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def shorten_url(
    request: Request,
    body: ShortenRequest,
    url_service: UrlService = Depends(get_url_service),
) -> ShortenResponse:
    """
    Shorten a long URL.

    Args:
        request: FastAPI request object.
        body: Validated request body with URL.
        url_service: URL service instance.

    Returns:
        ShortenResponse with short code and URLs.

    Raises:
        URLAlreadyExistsException: If URL already has a short code.
    """
    logger.info(f"Shortening URL: {body.url[:50]}...")

    result = await url_service.shorten_url(body.url)

    logger.info(f"Created short code: {result['short_code']}")

    return ShortenResponse(**result)
```

```python app/api/v1/redirect.py
"""
GET /{short_code} endpoint for URL redirection.
"""

import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from app.api.deps import get_url_service
from app.core.exceptions import (
    URLAlreadyDeletedException,
    URLExpiredException,
    URLNotFoundException,
)
from app.services.url_service import UrlService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/{short_code}",
    status_code=307,
    summary="Redirect to original URL",
    description="Redirect to the original URL using the short code.",
    responses={
        307: {"description": "Temporary redirect to original URL"},
        404: {"description": "Short code not found"},
        410: {"description": "URL has expired"},
    },
)
async def redirect_to_url(
    short_code: str,
    request: Request,
    url_service: UrlService = Depends(get_url_service),
) -> RedirectResponse:
    """
    Redirect to the original URL for a given short code.

    Args:
        short_code: The short code from the URL path.
        request: FastAPI request object.
        url_service: URL service instance.

    Returns:
        RedirectResponse with 307 status.

    Raises:
        URLNotFoundException: If short code not found.
        URLAlreadyDeletedException: If URL is deleted.
        URLExpiredException: If URL has expired.
    """
    logger.info(f"Redirect request for short_code: {short_code}")

    original_url = await url_service.get_original_url(short_code)

    logger.info(f"Redirecting {short_code} to {original_url[:50]}...")

    return RedirectResponse(
        url=original_url,
        status_code=307,
    )
```

```python app/api/v1/stats.py
"""
GET /stats/{short_code} endpoint for URL statistics.
"""

import logging

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_url_service
from app.schemas.stats import StatsResponse
from app.services.url_service import UrlService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/stats/{short_code}",
    response_model=StatsResponse,
    status_code=200,
    summary="Get URL statistics",
    description="Get click statistics and metadata for a short code.",
    responses={
        200: {"description": "Statistics retrieved successfully"},
        404: {"description": "Short code not found"},
    },
)
async def get_url_stats(
    short_code: str,
    request: Request,
    url_service: UrlService = Depends(get_url_service),
) -> StatsResponse:
    """
    Get statistics for a shortened URL.

    Args:
        short_code: The short code.
        request: FastAPI request object.
        url_service: URL service instance.

    Returns:
        StatsResponse with URL metadata and click count.

    Raises:
        URLNotFoundException: If short code not found.
    """
    logger.info(f"Stats request for short_code: {short_code}")

    stats = await url_service.get_stats(short_code)

    return StatsResponse(**stats)
```

```python app/api/v1/delete.py
"""
DELETE /{short_code} endpoint for URL deletion.
"""

import logging

from fastapi import APIRouter, Depends, Request, Response

from app.api.deps import get_url_service
from app.services.url_service import UrlService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.delete(
    "/{short_code}",
    status_code=204,
    summary="Delete a shortened URL",
    description="Soft delete a shortened URL by its short code.",
    responses={
        204: {"description": "URL successfully deleted"},
        404: {"description": "Short code not found"},
        409: {"description": "URL already deleted"},
    },
)
async def delete_url(
    short_code: str,
    request: Request,
    url_service: UrlService = Depends(get_url_service),
) -> Response:
    """
    Soft delete a shortened URL.

    Args:
        short_code: The short code to delete.
        request: FastAPI request object.
        url_service: URL service instance.

    Returns:
        Empty 204 response.

    Raises:
        URLNotFoundException: If short code not found.
        URLAlreadyDeletedException: If already deleted.
    """
    logger.info(f"Delete request for short_code: {short_code}")

    await url_service.delete_url(short_code)

    logger.info(f"Successfully deleted short_code: {short_code}")

    return Response(status_code=204)
```

```python app/main.py
"""
FastAPI application entry point.

Configures:
- Application lifespan (startup/shutdown)
- Exception handlers
- Rate limiting
- CORS
- API routers
- Health check endpoint
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.config import settings
from app.core.exceptions import (
    URLShortenerException,
    url_shortener_exception_handler,
    generic_exception_handler,
)
from app.core.rate_limiter import create_limiter, setup_rate_limiting
from app.db.redis_client import close_redis_pool, get_redis
from app.db.session import engine

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer(),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events:
    - Startup: Initialize connections
    - Shutdown: Close connections gracefully
    """
    logger.info("Starting URL Shortener service...")

    # Initialize Redis pool on startup
    try:
        redis = await get_redis()
        await redis.ping()
        logger.info("Redis connection established")
    except Exception as e:
        logger.warning(f"Redis not available on startup: {e}")

    yield

    # Cleanup on shutdown
    logger.info("Shutting down URL Shortener service...")
    await close_redis_pool()
    await engine.dispose()
    logger.info("Shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="URL Shortener",
        description="A high-performance URL shortening microservice",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Set up rate limiting
    limiter = create_limiter()
    setup_rate_limiting(app, limiter)

    # Configure CORS
    if settings.allowed_origins_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.allowed_origins_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Register exception handlers
    app.add_exception_handler(URLShortenerException, url_shortener_exception_handler)
    app.add_exception_handler(Exception, generic_exception_handler)

    # Include API routers
    app.include_router(v1_router)

    # Health check endpoint
    @app.get(
        "/health",
        summary="Health check",
        description="Check if the service and its dependencies are healthy.",
    )
    async def health_check(request: Request) -> JSONResponse:
        """
        Health check endpoint.

        Checks database and Redis connectivity.
        Returns 200 if all services are healthy, 503 otherwise.
        """
        health_status = {"status": "healthy", "checks": {}}

        # Check database
        try:
            from app.db.session import AsyncSessionLocal
            async with AsyncSessionLocal() as session:
                await session.execute("SELECT 1")
            health_status["checks"]["database"] = "healthy"
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["checks"]["database"] = f"unhealthy: {str(e)}"

        # Check Redis
        try:
            redis = await get_redis()
            await redis.ping()
            health_status["checks"]["redis"] = "healthy"
        except Exception as e:
            health_status["checks"]["redis"] = f"unhealthy: {str(e)}"
            # Redis is not critical - service can work without it
            if health_status["status"] == "healthy":
                health_status["status"] = "degraded"

        status_code = 200 if health_status["status"] == "healthy" else 503
        return JSONResponse(content=health_status, status_code=status_code)

    return app


# Create the application instance
app = create_app()
```

```python alembic/env.py
"""
Alembic environment configuration for async migrations.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.config import settings
from app.models.url import Base

# Alembic Config object
config = context.config

# Set up logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the database URL from settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Configures the context with just a URL and not an Engine.
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
    Run migrations with a live connection.

    Args:
        connection: SQLAlchemy connection.
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
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

```python alembic/versions/001_initial.py
"""
Initial migration: Create urls table.

Revision ID: 001
Revises: None
Create Date: 2025-01-15 10:00:00.000000
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
    """Create the urls table with indexes."""
    op.create_table(
        "urls",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("short_code", sa.String(10), nullable=False),
        sa.Column("original_url", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "is_deleted",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("short_code"),
    )

    # Create indexes
    op.create_index("idx_urls_short_code", "urls", ["short_code"], unique=True)
    op.create_index("idx_urls_created_at", "urls", ["created_at"])


def downgrade() -> None:
    """Drop the urls table and indexes."""
    op.drop_index("idx_urls_created_at", table_name="urls")
    op.drop_index("idx_urls_short_code", table_name="urls")
    op.drop_table("urls")
```

```python tests/__init__.py
"""
Test package for URL Shortener.
"""
```

```python tests/conftest.py
"""
Test fixtures for URL Shortener tests.

Provides:
- Test database (SQLite in-memory)
- Test Redis (or mock)
- Test HTTP client
- Test service instances
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.session import get_db
from app.db.redis_client import get_redis
from app.main import create_app
from app.models.url import Base
from app.repositories.url_repository import UrlRepository
from app.services.cache_service import CacheService
from app.services.code_generator import CodeGenerator
from app.services.url_service import UrlService


# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)

    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def test_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session


class MockRedis:
    """
    Mock Redis client for testing.

    Implements basic Redis operations used by CacheService.
    """

    def __init__(self):
        self._data: dict[str, str] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._ttls: dict[str, float] = {}

    async def get(self, key: str) -> str | None:
        return self._data.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self._data[key] = value
        self._ttls[key] = ttl

    async def delete(self, key: str) -> None:
        self._data.pop(key, None)
        self._ttls.pop(key, None)

    async def hincrby(self, key: str, field: str, amount: int) -> int:
        if key not in self._hashes:
            self._hashes[key] = {}
        current = int(self._hashes[key].get(field, 0))
        new_value = current + amount
        self._hashes[key][field] = str(new_value)
        return new_value

    async def hset(self, key: str, field: str, value: str) -> None:
        if key not in self._hashes:
            self._hashes[key] = {}
        self._hashes[key][field] = value

    async def hgetall(self, key: str) -> dict[str, str]:
        return self._hashes.get(key, {})

    async def ping(self) -> bool:
        return True

    def pipeline(self):
        return MockPipeline(self)


class MockPipeline:
    """Mock Redis pipeline for testing."""

    def __init__(self, redis: MockRedis):
        self.redis = redis
        self._commands: list = []

    def hincrby(self, key: str, field: str, amount: int):
        self._commands.append(("hincrby", key, field, amount))
        return self

    def hset(self, key: str, field: str, value: str):
        self._commands.append(("hset", key, field, value))
        return self

    async def execute(self) -> list:
        results = []
        for cmd in self._commands:
            if cmd[0] == "hincrby":
                result = await self.redis.hincrby(cmd[1], cmd[2], cmd[3])
                results.append(result)
            elif cmd[0] == "hset":
                await self.redis.hset(cmd[1], cmd[2], cmd[3])
                results.append(True)
        return results


@pytest_asyncio.fixture(scope="function")
async def mock_redis():
    """Create a mock Redis client."""
    return MockRedis()


@pytest_asyncio.fixture(scope="function")
def url_repository(test_session):
    """Create a URL repository for testing."""
    return UrlRepository(test_session)


@pytest_asyncio.fixture(scope="function")
def cache_service(mock_redis):
    """Create a cache service with mock Redis."""
    return CacheService(mock_redis)


@pytest_asyncio.fixture(scope="function")
def code_generator():
    """Create a code generator for testing."""
    return CodeGenerator(code_length=6)


@pytest_asyncio.fixture(scope="function")
def url_service(url_repository, cache_service, code_generator):
    """Create a URL service for testing."""
    return UrlService(
        repository=url_repository,
        cache_service=cache_service,
        code_generator=code_generator,
    )


@pytest_asyncio.fixture(scope="function")
async def test_app(test_session, mock_redis):
    """Create a test FastAPI application."""
    app = create_app()

    # Override dependencies
    async def override_get_db():
        yield test_session

    async def override_get_redis():
        return mock_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis] = override_get_redis

    return app


@pytest_asyncio.fixture(scope="function")
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """Create an async HTTP client for testing."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

```python tests/unit/__init__.py
"""
Unit tests package.
"""
```

```python tests/unit/test_base62.py
"""
Unit tests for base62 encoding/decoding.
"""

import pytest
from app.utils.base62 import encode_base62, decode_base62, BASE62_ALPHABET


class TestBase62Encode:
    """Tests for base62 encoding."""

    def test_encode_zero(self):
        """Zero should encode to '0'."""
        assert encode_base62(0) == "0"

    def test_encode_single_digit(self):
        """Single digits should encode correctly."""
        assert encode_base62(9) == "9"
        assert encode_base62(10) == "a"
        assert encode_base62(35) == "z"
        assert encode_base62(36) == "A"
        assert encode_base62(61) == "Z"

    def test_encode_two_digits(self):
        """Two-digit numbers should encode correctly."""
        assert encode_base62(62) == "10"
        assert encode_base62(123) == "1Z"
        assert encode_base62(3844) == "100"  # 62^2

    def test_encode_large_number(self):
        """Large numbers should encode correctly."""
        # 62^5 = 916132832
        assert encode_base62(916132832) == "100000"

    def test_encode_negative_raises(self):
        """Negative numbers should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative"):
            encode_base62(-1)

    def test_encode_decode_roundtrip(self):
        """Encoding then decoding should return the original number."""
        test_numbers = [0, 1, 10, 61, 62, 100, 1000, 999999]
        for num in test_numbers:
            encoded = encode_base62(num)
            decoded = decode_base62(encoded)
            assert decoded == num, f"Failed for {num}: {encoded} -> {decoded}"


class TestBase62Decode:
    """Tests for base62 decoding."""

    def test_decode_zero(self):
        """'0' should decode to 0."""
        assert decode_base62("0") == 0

    def test_decode_single_char(self):
        """Single characters should decode correctly."""
        assert decode_base62("9") == 9
        assert decode_base62("a") == 10
        assert decode_base62("z") == 35
        assert decode_base62("A") == 36
        assert decode_base62("Z") == 61

    def test_decode_two_chars(self):
        """Two-character strings should decode correctly."""
        assert decode_base62("10") == 62
        assert decode_base62("1Z") == 123

    def test_decode_empty_raises(self):
        """Empty string should raise ValueError."""
        with pytest.raises(ValueError, match="must not be empty"):
            decode_base62("")

    def test_decode_invalid_char_raises(self):
        """Invalid characters should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid base62 character"):
            decode_base62("!@#")

    def test_decode_all_valid_chars(self):
        """All base62 characters should be valid."""
        for i, char in enumerate(BASE62_ALPHABET):
            assert decode_base62(char) == i
```

```python tests/unit/test_url_validation.py
"""
Unit tests for URL validation and security checks.
"""

import pytest
from app.core.security import validate_url, is_private_ip
from app.core.exceptions import InvalidURLException


class TestValidateURL:
    """Tests for URL validation."""

    def test_valid_https_url(self):
        """Valid HTTPS URL should pass validation."""
        result = validate_url("https://example.com/path")
        assert result == "https://example.com/path"

    def test_valid_http_url(self):
        """Valid HTTP URL should pass validation."""
        result = validate_url("http://example.com")
        assert result == "http://example.com"

    def test_url_with_query_params(self):
        """URL with query parameters should pass."""
        result = validate_url("https://example.com/path?key=value&foo=bar")
        assert "?key=value&foo=bar" in result

    def test_url_with_fragment(self):
        """URL with fragment should pass."""
        result = validate_url("https://example.com/page#section")
        assert "#section" in result

    def test_invalid_scheme_ftp(self):
        """FTP scheme should be rejected."""
        with pytest.raises(InvalidURLException, match="Only http and https"):
            validate_url("ftp://example.com")

    def test_invalid_scheme_javascript(self):
        """javascript: scheme should be rejected."""
        with pytest.raises(InvalidURLException, match="Only http and https"):
            validate_url("javascript:alert(1)")

    def test_no_scheme(self):
        """URL without scheme should be rejected."""
        with pytest.raises(InvalidURLException, match="Only http and https"):
            validate_url("example.com")

    def test_empty_url(self):
        """Empty URL should be rejected."""
        with pytest.raises(InvalidURLException):
            validate_url("")

    def test_url_too_long(self):
        """URL exceeding 2048 characters should be rejected."""
        long_url = "https://example.com/" + "a" * 2040
        with pytest.raises(InvalidURLException, match="exceeds maximum length"):
            validate_url(long_url)

    def test_url_max_length(self):
        """URL at exactly 2048 characters should pass."""
        url = "https://example.com/" + "a" * 2020
        # Should be exactly 2048 chars
        assert len(url) == 2048
        result = validate_url(url)
        assert result == url

    def test_malformed_url(self):
        """Malformed URL should be rejected."""
        with pytest.raises(InvalidURLException):
            validate_url("not a url at all!!!")

    def test_url_without_host(self):
        """URL without host should be rejected."""
        with pytest.raises(InvalidURLException, match="valid domain"):
            validate_url("https://")


class TestPrivateIPBlocking:
    """Tests for private IP blocking (SSRF protection)."""

    def test_localhost_blocked(self):
        """localhost should be blocked."""
        assert is_private_ip("localhost") is True

    def test_loopback_ip_blocked(self):
        """127.0.0.1 should be blocked."""
        assert is_private_ip("127.0.0.1") is True

    def test_private_ip_blocked(self):
        """Private IP ranges should be blocked."""
        assert is_private_ip("192.168.1.1") is True
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("172.16.0.1") is True

    def test_public_ip_allowed(self):
        """Public IP should be allowed."""
        # Note: This test might fail if DNS resolution is not available
        # In CI/CD, we should mock DNS resolution
        assert is_private_ip("8.8.8.8") is False

    def test_zero_ip_blocked(self):
        """0.0.0.0 should be blocked."""
        assert is_private_ip("0.0.0.0") is True

    def test_link_local_blocked(self):
        """169.254.x.x should be blocked."""
        assert is_private_ip("169.254.1.1") is True
```

```python tests/unit/test_code_generator.py
"""
Unit tests for short code generation.
"""

import pytest
from app.services.code_generator import CodeGenerator


class TestCodeGenerator:
    """Tests for CodeGenerator."""

    def test_generate_default_length(self):
        """Generated code should have the default length."""
        generator = CodeGenerator(code_length=6)
        code = generator.generate(0)
        assert len(code) == 6

    def test_generate_custom_length(self):
        """Generated code should respect custom length."""
        generator = CodeGenerator(code_length=8)
        code = generator.generate(0)
        assert len(code) == 8

    def test_generate_different_inputs(self):
        """Different inputs should produce different codes."""
        generator = CodeGenerator(code_length=6)
        code1 = generator.generate(1)
        code2 = generator.generate(2)
        assert code1 != code2

    def test_generate_same_input_same_output(self):
        """Same input should produce same output (deterministic)."""
        generator = CodeGenerator(code_length=6)
        code1 = generator.generate(100)
        code2 = generator.generate(100)
        assert code1 == code2

    def test_generate_valid_base62(self):
        """Generated code should only contain base62 characters."""
        from app.utils.base62 import BASE62_ALPHABET

        generator = CodeGenerator(code_length=6)
        for i in range(100):
            code = generator.generate(i)
            for char in code:
                assert char in BASE62_ALPHABET, f"Invalid char '{char}' in code '{code}'"

    def test_generate_zero(self):
        """Zero should produce a padded code."""
        generator = CodeGenerator(code_length=6)
        code = generator.generate(0)
        # First char should be '0' (base62 of 0)
        assert code[0] == "0"
        assert len(code) == 6

    def test_generate_large_number(self):
        """Large numbers should produce valid codes."""
        generator = CodeGenerator(code_length=6)
        code = generator.generate(999999999)
        assert len(code) == 6

    def test_generate_with_retry_success(self):
        """generate_with_retry should succeed when code is available."""
        generator = CodeGenerator(code_length=6)

        def is_taken(code: str) -> bool:
            return False  # No codes are taken

        code = generator.generate_with_retry(0, is_taken)
        assert len(code) == 6

    def test_generate_with_retry_failure(self):
        """generate_with_retry should raise after max retries."""
        generator = CodeGenerator(code_length=6)

        def is_taken(code: str) -> bool:
            return True  # All codes are taken

        with pytest.raises(RuntimeError, match="Failed to generate"):
            generator.generate_with_retry(0, is_taken)
```

```python tests/integration/__init__.py
"""
Integration tests package.
"""
```

```python tests/integration/test_shorten.py
"""
Integration tests for POST /shorten endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestShortenEndpoint:
    """Integration tests for URL shortening."""

    async def test_shorten_valid_url(self, async_client: AsyncClient):
        """Should successfully shorten a valid URL."""
        response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/very/long/path"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "short_code" in data
        assert "short_url" in data
        assert "original_url" in data
        assert data["original_url"] == "https://example.com/very/long/path"
        assert len(data["short_code"]) == 6

    async def test_shorten_duplicate_url(self, async_client: AsyncClient):
        """Should return 409 for duplicate URL."""
        # First request
        await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/unique"},
        )

        # Second request with same URL
        response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/unique"},
        )

        assert response.status_code == 409
        data = response.json()
        assert "already shortened" in data["detail"].lower()

    async def test_shorten_invalid_url(self, async_client: AsyncClient):
        """Should return 400 for invalid URL."""
        response = await async_client.post(
            "/v1/shorten",
            json={"url": "not-a-valid-url"},
        )

        assert response.status_code == 400

    async def test_shorten_missing_url_field(self, async_client: AsyncClient):
        """Should return 422 for missing url field."""
        response = await async_client.post(
            "/v1/shorten",
            json={},
        )

        assert response.status_code == 422

    async def test_shorten_empty_url(self, async_client: AsyncClient):
        """Should return 400 for empty URL."""
        response = await async_client.post(
            "/v1/shorten",
            json={"url": ""},
        )

        assert response.status_code == 400

    async def test_shorten_url_with_special_chars(self, async_client: AsyncClient):
        """Should handle URLs with special characters."""
        response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/path?key=value&foo=bar%20baz"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "key=value" in data["original_url"]
```

```python tests/integration/test_redirect.py
"""
Integration tests for GET /{short_code} redirect endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRedirectEndpoint:
    """Integration tests for URL redirection."""

    async def test_redirect_existing_url(self, async_client: AsyncClient):
        """Should redirect to original URL for valid short code."""
        # First, create a short URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/target"},
        )
        short_code = create_response.json()["short_code"]

        # Then, access the short URL
        response = await async_client.get(
            f"/v1/{short_code}",
            follow_redirects=False,
        )

        assert response.status_code == 307
        assert response.headers["location"] == "https://example.com/target"

    async def test_redirect_nonexistent_code(self, async_client: AsyncClient):
        """Should return 404 for non-existent short code."""
        response = await async_client.get("/v1/nonexistent")

        assert response.status_code == 404

    async def test_redirect_deleted_url(self, async_client: AsyncClient):
        """Should return 404 for deleted URL."""
        # Create a short URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/to-delete"},
        )
        short_code = create_response.json()["short_code"]

        # Delete it
        await async_client.delete(f"/v1/{short_code}")

        # Try to access
        response = await async_client.get(f"/v1/{short_code}")

        assert response.status_code == 404

    async def test_redirect_increments_counter(self, async_client: AsyncClient):
        """Should increment click counter on redirect."""
        # Create a short URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/count-test"},
        )
        short_code = create_response.json()["short_code"]

        # Access it multiple times
        for _ in range(3):
            await async_client.get(f"/v1/{short_code}", follow_redirects=False)

        # Check stats
        stats_response = await async_client.get(f"/v1/stats/{short_code}")
        stats = stats_response.json()

        assert stats["clicks"] == 3
```

```python tests/integration/test_stats.py
"""
Integration tests for GET /stats/{short_code} endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestStatsEndpoint:
    """Integration tests for URL statistics."""

    async def test_stats_existing_url(self, async_client: AsyncClient):
        """Should return stats for existing URL."""
        # Create a short URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/stats-test"},
        )
        short_code = create_response.json()["short_code"]

        # Get stats
        response = await async_client.get(f"/v1/stats/{short_code}")

        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] == short_code
        assert data["original_url"] == "https://example.com/stats-test"
        assert "clicks" in data
        assert "created_at" in data
        assert data["clicks"] >= 0

    async def test_stats_nonexistent_code(self, async_client: AsyncClient):
        """Should return 404 for non-existent short code."""
        response = await async_client.get("/v1/stats/nonexistent")

        assert response.status_code == 404

    async def test_stats_deleted_url(self, async_client: AsyncClient):
        """Should return 404 for deleted URL."""
        # Create and delete
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/stats-deleted"},
        )
        short_code = create_response.json()["short_code"]
        await async_client.delete(f"/v1/{short_code}")

        # Try to get stats
        response = await async_client.get(f"/v1/stats/{short_code}")

        assert response.status_code == 404

    async def test_stats_with_clicks(self, async_client: AsyncClient):
        """Stats should reflect click count."""
        # Create URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/clicks-stats"},
        )
        short_code = create_response.json()["short_code"]

        # Generate some clicks
        for _ in range(5):
            await async_client.get(f"/v1/{short_code}", follow_redirects=False)

        # Check stats
        response = await async_client.get(f"/v1/stats/{short_code}")
        data = response.json()

        assert data["clicks"] == 5
```

```python tests/integration/test_delete.py
"""
Integration tests for DELETE /{short_code} endpoint.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestDeleteEndpoint:
    """Integration tests for URL deletion."""

    async def test_delete_existing_url(self, async_client: AsyncClient):
        """Should successfully delete an existing URL."""
        # Create URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/delete-me"},
        )
        short_code = create_response.json()["short_code"]

        # Delete it
        response = await async_client.delete(f"/v1/{short_code}")

        assert response.status_code == 204

    async def test_delete_nonexistent_code(self, async_client: AsyncClient):
        """Should return 404 for non-existent short code."""
        response = await async_client.delete("/v1/nonexistent")

        assert response.status_code == 404

    async def test_delete_already_deleted(self, async_client: AsyncClient):
        """Should return 409 for already deleted URL."""
        # Create and delete
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/double-delete"},
        )
        short_code = create_response.json()["short_code"]
        await async_client.delete(f"/v1/{short_code}")

        # Try to delete again
        response = await async_client.delete(f"/v1/{short_code}")

        assert response.status_code == 409

    async def test_delete_makes_url_inaccessible(self, async_client: AsyncClient):
        """Deleted URL should not be accessible."""
        # Create URL
        create_response = await async_client.post(
            "/v1/shorten",
            json={"url": "https://example.com/gone"},
        )
        short_code = create_response.json()["short_code"]

        # Delete it
        await async_client.delete(f"/v1/{short_code}")

        # Try to access
        response = await async_client.get(f"/v1/{short_code}")

        assert response.status_code == 404
```

```python tests/integration/test_rate_limiting.py
"""
Integration tests for rate limiting.

Note: These tests verify rate limiting behavior.
In test environment, rate limiting may be disabled or use in-memory storage.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestRateLimiting:
    """Integration tests for rate limiting."""

    async def test_multiple_requests_within_limit(self, async_client: AsyncClient):
        """Multiple requests within limit should succeed."""
        for _ in range(5):
            response = await async_client.post(
                "/v1/shorten",
                json={"url": f"https://example.com/test-{_}"},
            )
            assert response.status_code in (201, 409)  # 409 for duplicates is OK

    async def test_health_endpoint_no_limit(self, async_client: AsyncClient):
        """Health endpoint should not be rate limited."""
        for _ in range(10):
            response = await async_client.get("/health")
            assert response.status_code == 200
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
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml docker-compose.yml
version: "3.8"

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://shortener:shortener_pass@db:5432/shortener_db
      - REDIS_URL=redis://redis:6379/0
      - BASE_URL=http://localhost:8000
      - LOG_LEVEL=INFO
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=shortener
      - POSTGRES_PASSWORD=shortener_pass
      - POSTGRES_DB=shortener_db
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U shortener -d shortener_db"]
      interval: 5s
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
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

```ini alembic.ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = postgresql+asyncpg://shortener:shortener_pass@localhost:5432/shortener_db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

```markdown README.md
# URL Shortener Microservice

Высокопроизводительный микросервис для сокращения URL-адресов.

## Возможности

- Сокращение длинных URL до коротких кодов (6 символов, base62)
- Редирект по коротким ссылкам (307 Temporary Redirect)
- Статистика переходов
- Мягкое удаление ссылок (soft delete)
- Кэширование в Redis для быстрых редиректов
- Rate limiting для защиты от злоупотреблений
- SSRF-защита при валидации URL
- Полностью асинхронная архитектура (FastAPI + asyncpg + aioredis)

## Технологический стек

- **Python 3.11+**
- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0 (async)** — ORM
- **PostgreSQL 15** — основное хранилище
- **Redis 7** — кэш и счётчики
- **Alembic** — миграции БД
- **slowapi** — rate limiting
- **Docker** — контейнеризация

## Быстрый старт

### Предварительные требования

- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)

### Запуск через Docker Compose

```bash
# Клонировать репозиторий
git clone <repo-url>
cd url-shortener

# Скопировать .env.example в .env
cp .env.example .env

# Запустить сервисы
docker-compose up -d

# Применить миграции
docker-compose exec app alembic upgrade head
```

Сервис будет доступен по адресу `http://localhost:8000`.

Swagger документация: `http://localhost:8000/docs`

### Локальная разработка

```bash
# Создать виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Установить зависимости
pip install -r requirements.txt

# Запустить PostgreSQL и Redis (через Docker)
docker-compose up -d db redis

# Применить миграции
alembic upgrade head

# Запустить сервер
uvicorn app.main:app --reload --port 8000
```

### Запуск тестов

```bash
# Все тесты с покрытием
pytest --cov=app --cov-report=term-missing

# Только unit-тесты
pytest tests/unit/

# Только интеграционные тесты
pytest tests/integration/
```

## API Endpoints

### POST /v1/shorten
Создать короткую ссылку.

```bash
curl -X POST http://localhost:8000/v1/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/very/long/path"}'
```

### GET /v1/{short_code}
Перейти по короткой ссылке (редирект).

```bash
curl -L http://localhost:8000/v1/aB3x9Q
```

### GET /v1/stats/{short_code}
Получить статистику переходов.

```bash
curl http://localhost:8000/v1/stats/aB3x9Q
```

### DELETE /v1/{short_code}
Удалить короткую ссылку.

```bash
curl -X DELETE http://localhost:8000/v1/aB3x9Q
```

### GET /health
Проверка здоровья сервиса.

```bash
curl http://localhost:8000/health
```

## Переменные окружения

| Переменная | Описание | По умолчанию |
|-----------|----------|-------------|
| `DATABASE_URL` | DSN для PostgreSQL | `postgresql+asyncpg://...` |
| `REDIS_URL` | DSN для Redis | `redis://localhost:6379/0` |
| `SHORT_CODE_LENGTH` | Длина короткого кода | `6` |
| `CACHE_TTL_SECONDS` | TTL кэша в секундах | `86400` |
| `BASE_URL` | Базовый URL сервиса | `http://localhost:8000` |
| `RATE_LIMIT_SHORTEN` | Лимит для POST /shorten | `30/minute` |
| `RATE_LIMIT_DEFAULT` | Лимит для остальных | `100/minute` |
| `BLOCK_PRIVATE_IPS` | Блокировка SSRF | `true` |
| `ALLOWED_ORIGINS` | CORS origins | `""` |

## Архитектура

```
Client → FastAPI → Service Layer → Repository (PostgreSQL)
                    ↓
                 Cache Manager (Redis)
```

- **API Layer**: Валидация запросов, rate limiting
- **Service Layer**: Бизнес-логика
- **Repository Layer**: Доступ к данным
- **Cache Manager**: Кэширование и счётчики

## Лицензия

MIT
```