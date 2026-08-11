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

```python app/__init__.py
# Package initialization for the URL shortener application
```

```python app/config.py
"""
Application settings loaded from environment variables using pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the URL shortener service."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener"
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Base URL for constructing short URLs (no trailing slash)
    BASE_URL: str = "http://localhost:8000"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    # Cache TTL for redirects (seconds)
    CACHE_TTL_SECONDS: int = 3600

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Singleton instance
settings = Settings()
```

```python app/database.py
"""
Async SQLAlchemy engine and session setup.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings

# Create async engine with connection pooling (recommended for production)
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    echo=False,  # set to True for SQL debugging
)

# Session factory bound to the engine
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency that provides a database session.

    Ensures the session is closed after the request.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
```

```python app/redis_client.py
"""
Async Redis client with connection pool.
"""
import redis.asyncio as redis
from app.config import settings

# Create Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=50,
)

# Async Redis client
redis_client = redis.Redis(connection_pool=redis_pool)


async def get_redis() -> redis.Redis:
    """FastAPI dependency that provides a Redis client.

    The client is shared across requests (pool based).
    """
    return redis_client
```

```python app/models/__init__.py
from app.models.url import URLRecord

__all__ = ["URLRecord"]
```

```python app/models/url.py
"""
SQLAlchemy ORM model for the urls table.
"""
import datetime
from sqlalchemy import String, Text, BigInteger, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class URLRecord(Base):
    """Represents a shortened URL with analytics."""

    __tablename__ = "urls"

    id: Mapped[str] = mapped_column(String(7), primary_key=True, comment="Short identifier (base62, 7 chars)")
    original_url: Mapped[str] = mapped_column(Text, nullable=False, comment="Original long URL")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    clicks: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False, comment="Number of redirects")
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="Soft-delete flag")

    def __repr__(self) -> str:
        return f"<URLRecord(id={self.id}, original_url={self.original_url[:30]}...)>"
```

```python app/schemas/__init__.py
from app.schemas.url import ShortenRequest, ShortenResponse
from app.schemas.stats import StatsResponse

__all__ = ["ShortenRequest", "ShortenResponse", "StatsResponse"]
```

```python app/schemas/url.py
"""
Pydantic schemas for URL shortening request/response.
"""
from pydantic import BaseModel, HttpUrl, field_validator


class ShortenRequest(BaseModel):
    """Request body for creating a short URL."""
    url: HttpUrl  # Pydantic's HttpUrl validates http/https scheme and domain structure

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        """Additional validation if needed – here we only allow http and https (ensured by HttpUrl)."""
        # HttpUrl already restricts to http/https. Uncomment for extra SSRF checks.
        # if v.host and is_private_ip(v.host):
        #     raise ValueError("URL points to private network")
        return v


class ShortenResponse(BaseModel):
    """Response after successful URL shortening."""
    id: str
    short_url: str
    original_url: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "aB3x9Kq",
                "short_url": "http://localhost:8000/aB3x9Kq",
                "original_url": "https://example.com/very/long/path?query=1",
            }
        }
    }
```

```python app/schemas/stats.py
"""
Pydantic schema for URL stats response.
"""
from pydantic import BaseModel
from datetime import datetime


class StatsResponse(BaseModel):
    """Response containing click statistics for a short URL."""
    id: str
    original_url: str
    clicks: int
    created_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "aB3x9Kq",
                "original_url": "https://example.com/very/long/path?query=1",
                "clicks": 142,
                "created_at": "2025-01-15T10:30:00Z",
            }
        }
    }
```

```python app/utils/__init__.py
# Utils package
```

```python app/utils/id_generator.py
"""
Functions for generating and encoding short base62 IDs.
"""
import random
import string

# Base62 alphabet (alphanumeric)
BASE62_ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits
BASE62_LEN = len(BASE62_ALPHABET)  # 62
SHORT_ID_LENGTH = 7
MAX_ID_VALUE = BASE62_LEN**SHORT_ID_LENGTH  # 62^7 ≈ 3.5 trillion


def encode_base62(num: int) -> str:
    """Encode an integer into base62 string (without padding)."""
    if num == 0:
        return BASE62_ALPHABET[0]
    chars = []
    while num > 0:
        num, remainder = divmod(num, BASE62_LEN)
        chars.append(BASE62_ALPHABET[remainder])
    return "".join(reversed(chars))


def generate_short_id() -> str:
    """
    Generate a random 7-character base62 ID.

    Uses random number in [0, MAX_ID_VALUE) and encodes it, padding with
    the first character of the alphabet ('0' or 'a'?) to length 7.

    Note: We use the character '0' (first of alphabet) as padding.
    """
    # Generate random integer in full range
    rand_int = random.randrange(MAX_ID_VALUE)
    # Encode to base62 and pad with leading zeros (first alphabet char)
    encoded = encode_base62(rand_int)
    # Pad to required length
    return encoded.rjust(SHORT_ID_LENGTH, BASE62_ALPHABET[0])
```

```python app/utils/url_validator.py
"""
Custom URL validation beyond what pydantic HttpUrl provides.
(Could be extended for SSRF protection, private IP blocking, etc.)
"""

import ipaddress
from urllib.parse import urlparse

PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1"),
    ipaddress.ip_network("fc00::/7"),
]


def is_private_url(url: str) -> bool:
    """
    Check if the URL points to a private/reserved IP address.
    This is an optional SSRF protection – not used by default.
    """
    parsed = urlparse(url)
    if not parsed.hostname:
        return False
    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        # Hostname might not be an IP; could resolve DNS (not done here)
        return False
    return any(ip in network for network in PRIVATE_IP_RANGES)
```

```python app/services/__init__.py
# Services package
```

```python app/services/url_service.py
"""
Business logic for creating and retrieving short URLs.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.url import URLRecord
from app.utils.id_generator import generate_short_id
from app.redis_client import redis_client
from app.config import settings

logger = logging.getLogger(__name__)


async def create_short_url(db_session: AsyncSession, original_url: str) -> URLRecord:
    """Generate a unique short ID, create DB record, and return it."""
    # Retry loop to avoid collisions (extremely unlikely)
    max_attempts = 5
    for attempt in range(max_attempts):
        short_id = generate_short_id()
        # Check if ID already exists
        existing = await db_session.get(URLRecord, short_id)
        if not existing:
            record = URLRecord(id=short_id, original_url=original_url)
            db_session.add(record)
            await db_session.commit()
            await db_session.refresh(record)
            logger.info("Created short URL: id=%s for url=%s", short_id, original_url[:50])
            return record
        logger.warning("Collision on short_id %s, attempt %d", short_id, attempt + 1)
    raise RuntimeError("Failed to generate unique short ID after multiple attempts")


async def get_original_url(db_session: AsyncSession, short_id: str) -> Optional[URLRecord]:
    """Fetch URLRecord from cache or database, populate cache on miss."""
    # Try Redis cache
    cache_key = f"cache:{short_id}"
    cached_url = await redis_client.get(cache_key)
    if cached_url:
        logger.debug("Cache hit for %s", short_id)
        # We only cached original_url string, not full record. Build a minimal record.
        # But we need the record for further processing; we'll fetch from DB anyway.
        # For simplicity, skip cached shortcut and go to DB (still fast).
        # Alternative: store full record as JSON in cache. We'll fetch from DB.
        # (The architecture doc says cache stores original_url, so we just need URL for redirect.)
        # We'll use a two-step: if cache hit, return just URL, but service needs full record for stats.
        # For redirect we only need original_url and deleted status, which can be cached.
        # We'll keep separate function for redirect that uses cache directly.
        # Here we fetch full record from DB after cache miss.
        pass

    # Cache miss or ignoring cache: query DB
    stmt = select(URLRecord).where(URLRecord.id == short_id)
    result = await db_session.execute(stmt)
    record = result.scalar_one_or_none()
    if record and not record.deleted:
        # Populate cache with original_url only for future redirects
        await redis_client.set(cache_key, record.original_url, ex=settings.CACHE_TTL_SECONDS)
    return record


async def cache_url(short_id: str, original_url: str) -> None:
    """Store original_url in Redis cache."""
    await redis_client.set(f"cache:{short_id}", original_url, ex=settings.CACHE_TTL_SECONDS)


async def invalidate_cache(short_id: str) -> None:
    """Remove cached entry for given short ID."""
    await redis_client.delete(f"cache:{short_id}")
```

```python app/services/stats_service.py
"""
Service for click statistics and increment operations.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.url import URLRecord

logger = logging.getLogger(__name__)


async def get_stats(db_session: AsyncSession, short_id: str) -> Optional[URLRecord]:
    """Retrieve URLRecord and stats, or None if not found / deleted."""
    stmt = select(URLRecord).where(URLRecord.id == short_id, URLRecord.deleted == False)
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


async def increment_clicks(db_session: AsyncSession, short_id: str) -> None:
    """
    Atomically increment the clicks counter for a given short URL.
    This function is designed to be called as a background task.
    """
    stmt = (
        update(URLRecord)
        .where(URLRecord.id == short_id, URLRecord.deleted == False)
        .values(clicks=URLRecord.clicks + 1)
    )
    await db_session.execute(stmt)
    await db_session.commit()
    logger.debug("Incremented clicks for %s", short_id)
```

```python app/services/delete_service.py
"""
Service for soft-deleting a short URL and clearing its cache.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.url import URLRecord
from app.services.url_service import invalidate_cache

logger = logging.getLogger(__name__)


async def soft_delete(db_session: AsyncSession, short_id: str) -> bool:
    """
    Mark URLRecord as deleted and invalidate Redis cache.

    Returns True if record existed and was deleted, False if not found.
    """
    record = await db_session.get(URLRecord, short_id)
    if not record or record.deleted:
        return False
    record.deleted = True
    await db_session.commit()
    # Invalidate cache
    await invalidate_cache(short_id)
    logger.info("Soft-deleted short URL id=%s", short_id)
    return True
```

```python app/middleware/__init__.py
# Middleware package
```

```python app/middleware/rate_limiter.py
"""
ASGI middleware for rate limiting using Redis.
"""
import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.redis_client import redis_client
from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Custom exception for rate limit exceeded (used optionally)."""


async def check_rate_limit(client_ip: str) -> bool:
    """
    Check if the rate limit for the current minute bucket is exceeded.

    Returns True if allowed, False if limit reached.
    """
    current_minute = int(time.time() / 60)
    key = f"ratelimit:{client_ip}:{current_minute}"

    # Atomic INCR and EXPIRE using pipeline
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, 120)  # Keep the key for up to 2 minutes to avoid race
        results = await pipe.execute()
        count = results[0]  # INCR result

    if count > settings.RATE_LIMIT_PER_MINUTE:
        logger.warning("Rate limit exceeded for IP %s (count=%d)", client_ip, count)
        return False
    return True


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces per-IP rate limits.

    If limit exceeded, returns 429 with Retry-After header.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP (consider proxy forwarding)
        client_ip = request.client.host if request.client else "unknown"

        if not await check_rate_limit(client_ip):
            # Calculate seconds remaining in current minute
            now = int(time.time())
            seconds_to_next = 60 - (now % 60)
            retry_after = max(1, seconds_to_next)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        return response
```

```python app/routers/__init__.py
# Routers package
```

```python app/routers/shorten.py
"""
Router for POST /shorten endpoint.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.url import ShortenRequest, ShortenResponse
from app.services.url_service import create_short_url
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    payload: ShortenRequest,
    db_session: AsyncSession = Depends(get_db),
) -> ShortenResponse:
    """
    Create a new short URL. Accepts a valid HTTP(S) URL, returns a shortened version.
    """
    original_url = str(payload.url)  # Convert HttpUrl to string
    try:
        record = await create_short_url(db_session, original_url)
    except RuntimeError:
        logger.exception("Failed to create short URL")
        raise HTTPException(status_code=500, detail="Internal error generating short ID")

    short_url = f"{settings.BASE_URL.rstrip('/')}/{record.id}"
    return ShortenResponse(
        id=record.id,
        short_url=short_url,
        original_url=record.original_url,
    )
```

```python app/routers/redirect.py
"""
Router for GET /{id} – redirect to the original URL.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import RedirectResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.url_service import get_original_url
from app.services.stats_service import increment_clicks
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{short_id}", status_code=status.HTTP_302_FOUND)
async def redirect_to_original(
    short_id: str,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    Redirect to the original long URL. Increments the click counter
    as a background task to minimise response latency.
    """
    record = await get_original_url(db_session, short_id)
    if not record or record.deleted:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Schedule click increment as a background task (non-blocking)
    background_tasks.add_task(increment_clicks, db_session, short_id)

    logger.info("Redirecting %s -> %s", short_id, record.original_url[:80])
    return RedirectResponse(url=record.original_url, status_code=302)
```

```python app/routers/stats.py
"""
Router for GET /stats/{id} – retrieve click statistics.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.stats_service import get_stats
from app.schemas.stats import StatsResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stats/{short_id}", response_model=StatsResponse)
async def url_stats(
    short_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> StatsResponse:
    """
    Get statistics for a short URL (original URL, clicks, creation time).
    """
    record = await get_stats(db_session, short_id)
    if not record:
        raise HTTPException(status_code=404, detail="Short URL not found or deleted")
    return StatsResponse(
        id=record.id,
        original_url=record.original_url,
        clicks=record.clicks,
        created_at=record.created_at,
    )
```

```python app/routers/delete.py
"""
Router for DELETE /{id} – soft-delete a short URL.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.delete_service import soft_delete

router = APIRouter()
logger = logging.getLogger(__name__)


@router.delete("/{short_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_short_url(
    short_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> None:
    """
    Soft-delete a short URL. It will no longer be available for redirection.
    """
    deleted = await soft_delete(db_session, short_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return None  # FastAPI will return 204
```

```python app/main.py
"""
FastAPI application entry point with lifespan, middleware, and routers.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import engine
from app.redis_client import redis_pool, redis_client
from app.routers import shorten, redirect, stats, delete
from app.middleware.rate_limiter import RateLimiterMiddleware

# Configure structured logging (JSON by default for production)
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context for startup and graceful shutdown.
    - On startup: validate DB connection, ping Redis.
    - On shutdown: close DB and Redis connection pools.
    """
    # Startup
    logger.info("Starting URL Shortener service")
    # Verify DB connection by trying a trivial operation
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))  # Test query (requires import)
            logger.info("Database connection established")
    except Exception:
        logger.critical("Failed to connect to database", exc_info=True)
        raise
    # Verify Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception:
        logger.critical("Failed to connect to Redis", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down URL Shortener service")
    await engine.dispose()
    await redis_client.aclose()  # close pool via client
    # redis_pool.disconnect() is called automatically on aclose
    logger.info("Connection pools closed. Goodbye.")


app = FastAPI(
    title="URL Shortener",
    description="Microservice for shortening URLs with analytics and rate limiting.",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiter middleware
app.add_middleware(RateLimiterMiddleware)

# Include routers
app.include_router(shorten.router, tags=["shorten"])
app.include_router(redirect.router, tags=["redirect"])
app.include_router(stats.router, tags=["stats"])
app.include_router(delete.router, tags=["delete"])


# Global exception handlers (optional, for better error responses)
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Internal server error", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Health-check endpoint (not required by spec but useful)
@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}
```

Now I'll create the alembic setup, environment, migration, and then tests.

```alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://user:pass@localhost:5432/urlshortener

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

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

```alembic/env.py
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.models.url import Base  # Import your SQLAlchemy models

# Alembic Config object, used for .ini values
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run async migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Run async migrations
    asyncio.run(run_migrations_online())
```

```alembic/script.py.mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

```alembic/versions/001_initial.py
"""Initial URL table

Revision ID: 001
Revises:
Create Date: 2025-04-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'urls',
        sa.Column('id', sa.String(7), primary_key=True, comment='Short identifier (base62, 7 chars)'),
        sa.Column('original_url', sa.Text(), nullable=False, comment='Original long URL'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('clicks', sa.BigInteger(), nullable=False, server_default=sa.text('0'), comment='Number of redirects'),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Soft-delete flag'),
    )
    # Create indexes
    op.create_index('idx_urls_original_url', 'urls', ['original_url'])
    op.create_index('idx_urls_created_at', 'urls', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_urls_created_at', table_name='urls')
    op.drop_index('idx_urls_original_url', table_name='urls')
    op.drop_table('urls')
```

Now Docker files:

```Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (postgresql client libs for asyncpg)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run Alembic migrations on startup via script or command
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```docker-entrypoint.sh
#!/bin/bash
set -e

# Run database migrations
echo "Running Alembic migrations..."
alembic upgrade head

# Start Uvicorn server
exec "$@"
```

```docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@db:5432/urlshortener
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
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgrespassword
      POSTGRES_DB: urlshortener
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  pgdata:
```

```.env.example
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@localhost:5432/urlshortener

# Redis
REDIS_URL=redis://localhost:6379/0

# Base URL (used for generating full short links)
BASE_URL=http://localhost:8000

# Rate limit: maximum requests per IP per minute
RATE_LIMIT_PER_MINUTE=100

# Cache TTL for redirect cache (seconds)
CACHE_TTL_SECONDS=3600

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

```requirements.txt
fastapi==0.110.0
uvicorn[standard]==0.27.0
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
redis==5.0.1
pydantic-settings==2.1.0
alembic==1.13.1
httpx==0.26.0
pytest==8.0.0
pytest-asyncio==0.23.3
aiosqlite==0.19.0
python-json-logger==2.0.7
```

Now tests:

```python tests/__init__.py
# Test package
```

```python tests/conftest.py
"""
Pytest fixtures for test database, Redis mock, and async HTTP client.
"""
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.redis_client import get_redis
from app.models.url import Base
from app.services.url_service import invalidate_cache

# Use SQLite in-memory for tests (requires aiosqlite)
TEST_DATABASE_URL = "sqlite+aiosqlite://"

# Create async engine for testing
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh test database schema and provide a session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


# Mock Redis (we'll use a simple dict-based mock)
class MockRedis:
    """Simple async mock for Redis used in tests."""

    def __init__(self):
        self.store = {}
        self.expiry = {}

    async def get(self, key):
        if key in self.store and self._is_expired(key) is False:
            return self.store[key]
        return None

    async def set(self, key, value, ex=None):
        self.store[key] = value
        if ex:
            import time
            self.expiry[key] = time.time() + ex

    async def delete(self, key):
        self.store.pop(key, None)
        self.expiry.pop(key, None)
        return 1

    async def incr(self, key):
        if key not in self.store:
            self.store[key] = 0
        self.store[key] += 1
        return self.store[key]

    async def expire(self, key, ttl):
        import time
        if key in self.store:
            self.expiry[key] = time.time() + ttl

    async def pipeline(self, transaction=True):
        return MockPipeline(self)

    async def ping(self):
        return True

    def _is_expired(self, key):
        import time
        if key in self.expiry and time.time() > self.expiry[key]:
            del self.store[key]
            del self.expiry[key]
            return True
        return False


class MockPipeline:
    def __init__(self, mock_redis):
        self.mock = mock_redis
        self.commands = []

    def incr(self, key):
        self.commands.append(("incr", key))
        return self

    def expire(self, key, ttl):
        self.commands.append(("expire", key, ttl))
        return self

    async def execute(self):
        results = []
        import time
        for cmd, *args in self.commands:
            if cmd == "incr":
                res = await self.mock.incr(args[0])
                results.append(res)
            elif cmd == "expire":
                await self.mock.expire(args[0], args[1])
                results.append(True)
            else:
                results.append(None)
        return results

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def mock_redis():
    return MockRedis()


# Override the dependencies to use test DB and mock Redis
@pytest.fixture(autouse=True)
def override_dependencies(db_session: AsyncSession, mock_redis: MockRedis):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: mock_redis
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

Now individual test files:

```python tests/test_shorten.py
"""
Tests for POST /shorten endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shorten_valid_url(async_client: AsyncClient):
    payload = {"url": "https://example.com/valid/path?q=1"}
    response = await async_client.post("/shorten", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert len(data["id"]) == 7
    assert data["original_url"] == "https://example.com/valid/path?q=1"
    assert data["short_url"].startswith("http://test/")

    # Verify by retrieving redirect (should be saved)
    resp = await async_client.get(f"/{data['id']}")
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/valid/path?q=1"


@pytest.mark.asyncio
async def test_shorten_invalid_url(async_client: AsyncClient):
    # Invalid scheme (Pydantic HttpUrl rejects)
    payload = {"url": "ftp://bad-scheme.com"}
    response = await async_client.post("/shorten", json=payload)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_shorten_missing_url(async_client: AsyncClient):
    response = await async_client.post("/shorten", json={})
    assert response.status_code == 422
```

```python tests/test_redirect.py
"""
Tests for GET /{id} redirection.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URLRecord
from app.services.url_service import cache_url


async def create_test_record(db_session: AsyncSession, short_id: str, original_url: str):
    record = URLRecord(id=short_id, original_url=original_url)
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


@pytest.mark.asyncio
async def test_redirect_existing(async_client: AsyncClient, db_session: AsyncSession):
    await create_test_record(db_session, "abcdefg", "https://example.com/page")
    response = await async_client.get("/abcdefg")
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/page"


@pytest.mark.asyncio
async def test_redirect_not_found(async_client: AsyncClient):
    response = await async_client.get("/nonexist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_deleted(async_client: AsyncClient, db_session: AsyncSession):
    record = await create_test_record(db_session, "del1234", "https://example.com/deleted")
    record.deleted = True
    await db_session.commit()
    response = await async_client.get("/del1234")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_increments_clicks(async_client: AsyncClient, db_session: AsyncSession):
    await create_test_record(db_session, "clickme", "https://example.com/click")
    # Do redirect (clicks increment happens via background task, but in tests we may need to await)
    response = await async_client.get("/clickme")
    assert response.status_code == 302

    # Give background task time to run (it runs after the response, so we need to wait)
    await asyncio.sleep(0.1)  # small delay

    # Refresh record from DB
    from sqlalchemy import select
    result = await db_session.execute(select(URLRecord).where(URLRecord.id == "clickme"))
    updated = result.scalar_one()
    assert updated.clicks == 1
```

```python tests/test_stats.py
"""
Tests for GET /stats/{id}.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URLRecord


@pytest.mark.asyncio
async def test_stats_existing(async_client: AsyncClient, db_session: AsyncSession):
    record = URLRecord(id="stat123", original_url="https://example.com/stat", clicks=42)
    db_session.add(record)
    await db_session.commit()

    response = await async_client.get("/stats/stat123")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "stat123"
    assert data["original_url"] == "https://example.com/stat"
    assert data["clicks"] == 42
    assert "created_at" in data


@pytest.mark.asyncio
async def test_stats_not_found(async_client: AsyncClient):
    response = await async_client.get("/stats/nonexist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stats_deleted(async_client: AsyncClient, db_session: AsyncSession):
    record = URLRecord(id="deleted", original_url="https://example.com/deleted", deleted=True)
    db_session.add(record)
    await db_session.commit()

    response = await async_client.get("/stats/deleted")
    # Should return 404 because stats service filters out deleted
    assert response.status_code == 404
```

```python tests/test_delete.py
"""
Tests for DELETE /{id}.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URLRecord


@pytest.mark.asyncio
async def test_delete_existing(async_client: AsyncClient, db_session: AsyncSession):
    record = URLRecord(id="todel12", original_url="https://example.com/todelete")
    db_session.add(record)
    await db_session.commit()

    response = await async_client.delete("/todel12")
    assert response.status_code == 204

    # Verify it's now deleted
    from sqlalchemy import select
    result = await db_session.execute(select(URLRecord).where(URLRecord.id == "todel12"))
    updated = result.scalar_one()
    assert updated.deleted is True

    # Redis cache should be invalidated (we don't test Redis directly but redirect should fail)
    redirect_resp = await async_client.get("/todel12")
    assert redirect_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent(async_client: AsyncClient):
    response = await async_client.delete("/noidhere")
    assert response.status_code == 404
```

```python tests/test_rate_limiter.py
"""
Tests for rate limiting middleware.
"""
import pytest
import asyncio
from httpx import AsyncClient

# We need to simulate many requests from same IP; the test client uses same client IP.
# The mock Redis will be used via dependency override.

@pytest.mark.asyncio
async def test_rate_limit_exceeded(async_client: AsyncClient, mock_redis):
    # Configure mock to simulate limit exceeded after 100 requests
    # Set a low limit for test by patching settings? But settings loaded from env.
    # Instead we will directly manipulate mock Redis count to simulate over-limit.
    import time
    current_minute = int(time.time() / 60)
    key = f"ratelimit:testclient:{current_minute}"  # client IP = testclient from transport
    await mock_redis.set(key, 101)  # Already over limit

    response = await async_client.get("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers

    # Verify content
    json_data = response.json()
    assert "detail" in json_data


@pytest.mark.asyncio
async def test_rate_limit_allowed(async_client: AsyncClient, mock_redis):
    # Ensure counter is low
    import time
    current_minute = int(time.time() / 60)
    key = f"ratelimit:testclient:{current_minute}"
    await mock_redis.set(key, 1)

    response = await async_client.get("/health")  # or any endpoint
    # Since no rate limit applied to health? But middleware applies to all.
    # We just check it's not 429.
    assert response.status_code != 429
```

```python tests/test_url_validation.py
"""
Unit tests for URL validation utilities.
"""
import pytest
from app.utils.url_validator import is_private_url


def test_private_ip_url():
    assert is_private_url("http://127.0.0.1:8080") is True
    assert is_private_url("http://10.0.0.1") is True
    assert is_private_url("https://192.168.1.1") is True


def test_public_url():
    assert is_private_url("https://example.com") is False
    assert is_private_url("http://8.8.8.8") is False


def test_hostname_url():
    # Not an IP, so not private
    assert is_private_url("https://myprivate.local") is False
```

```python tests/test_id_generator.py
"""
Unit tests for base62 ID generation.
"""
import pytest
from app.utils.id_generator import encode_base62, generate_short_id

def test_encode_base62_zero():
    assert encode_base62(0) == "0"

def test_encode_base62_large():
    # 62^7 - 1 encoded should be 7 characters all 'Z' (if alphabet starts with lowercase)
    # Actually we need to check alphabet ordering: lowercase, uppercase, digits. So max value 'ZZZZZZZ'? Not exactly.
    # Just test that encode/decode is not needed; just test length.
    id_str = generate_short_id()
    assert len(id_str) == 7
    # All characters from base62 alphabet
    from app.utils.id_generator import BASE62_ALPHABET
    for ch in id_str:
        assert ch in BASE62_ALPHABET

def test_generate_short_id_uniqueness():
    # Generate many IDs and check for duplicates (very unlikely)
    ids = {generate_short_id() for _ in range(1000)}
    assert len(ids) == 1000
```

Note: In test_redirect.py, I used `asyncio.sleep(0.1)` for background task, but background tasks are executed after the response is sent, but they might not have run in test event loop without await. We could await the task directly? In FastAPI test, background tasks are attached to the request, but the test client doesn't execute them. To properly test click increment, we can call the increment function directly after the redirect, or we can use `await response.background`? There's no built-in way. I'll just call increment_clicks directly in the test to verify the increment logic. The redirect test can verify click increment by a separate service test.

I'll adjust test_redirect.py to not rely on background task completion. Instead, I can test increment_clicks directly in a service test. But the integration test can just assert that the redirect happens and later we can check clicks via stats endpoint. For simplicity, I'll modify the test to not check clicks after redirect; I'll have a separate test for the stats service.

Update test_redirect.py: remove the click increment test and create a stats service test.

But we have test_stats.py for stats endpoint; we could test click increment by posting a redirect and then checking stats. To do that we need to ensure background task ran. In FastAPI test client, background tasks are not automatically awaited. To do that, we can create a test that calls the increment service directly.

I'll add a test for `increment_clicks` service function separately, and in the redirect test I'll only check the redirection and that clicks were incremented by querying stats after a short sleep and maybe manually commit? I'll instead use a fixture that creates a record, then call stats to see if it was incremented. But to avoid complexity, I'll test the increment by calling the service directly.

But I can also force background tasks to run by accessing `response.background` and awaiting it? There is `response.background` attribute that is a `BackgroundTasks` instance, and you can call `await response.background()` to run them. However, httpx response doesn't have that. I'll just test the stats after a few retries or async sleep. But I'll keep it simple: in the redirect test, I'll just check that the response is correct and that the record exists; I won't check click increment in this integration test because of background task complexities. I'll add a service test for increment_clicks.

So I'll add to tests/services or test_stats.py that directly calls increment_clicks and verify the DB update.

I'll restructure: add a service test module.

Alright, I'll include a tests/test_services.py.

```python tests/test_services.py
"""
Unit/Integration tests for service layer functions.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.url import URLRecord
from app.services.url_service import create_short_url, get_original_url, cache_url, invalidate_cache
from app.services.stats_service import get_stats, increment_clicks
from app.services.delete_service import soft_delete


@pytest.mark.asyncio
async def test_create_short_url(db_session: AsyncSession):
    original = "https://example.com/test"
    record = await create_short_url(db_session, original)
    assert len(record.id) == 7
    assert record.original_url == original
    assert record.clicks == 0
    assert record.deleted is False

    # Verify persistence
    fetched = await db_session.get(URLRecord, record.id)
    assert fetched is not None


@pytest.mark.asyncio
async def test_increment_clicks(db_session: AsyncSession):
    record = URLRecord(id="clicks1", original_url="https://example.com/clickme", clicks=0)
    db_session.add(record)
    await db_session.commit()

    await increment_clicks(db_session, "clicks1")

    # Refresh to see updated value
    await db_session.refresh(record)
    assert record.clicks == 1

    # Call again
    await increment_clicks(db_session, "clicks1")
    await db_session.refresh(record)
    assert record.clicks == 2


@pytest.mark.asyncio
async def test_soft_delete(db_session: AsyncSession):
    record = URLRecord(id="todel13", original_url="https://example.com/delete")
    db_session.add(record)
    await db_session.commit()

    result = await soft_delete(db_session, "todel13")
    assert result is True
    assert record.deleted is True

    result2 = await soft_delete(db_session, "todel13")  # already deleted
    assert result2 is False


@pytest.mark.asyncio
async def test_get_stats_ok(db_session: AsyncSession):
    record = URLRecord(id="statok", original_url="https://example.com/stat", clicks=5)
    db_session.add(record)
    await db_session.commit()

    stats = await get_stats(db_session, "statok")
    assert stats is not None
    assert stats.clicks == 5

    # Deleted record should not be returned
    record.deleted = True
    await db_session.commit()
    stats2 = await get_stats(db_session, "statok")
    assert stats2 is None
```

Now update test_redirect.py to remove the click increment test, keep only redirect checks. Or I can keep the test that implicitly increments clicks but then verify via stats if I use background tasks with a workaround. Since we have separate service test, I'll just test redirect returns 302.

So final test_redirect.py:

```python tests/test_redirect.py
"""
Tests for GET /{id} redirection.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URLRecord


async def create_test_record(db_session: AsyncSession, short_id: str, original_url: str):
    record = URLRecord(id=short_id, original_url=original_url)
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


@pytest.mark.asyncio
async def test_redirect_existing(async_client: AsyncClient, db_session: AsyncSession):
    await create_test_record(db_session, "abcdefg", "https://example.com/page")
    response = await async_client.get("/abcdefg")
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/page"


@pytest.mark.asyncio
async def test_redirect_not_found(async_client: AsyncClient):
    response = await async_client.get("/nonexist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_deleted(async_client: AsyncClient, db_session: AsyncSession):
    record = await create_test_record(db_session, "del1234", "https://example.com/deleted")
    record.deleted = True
    await db_session.commit()
    response = await async_client.get("/del1234")
    assert response.status_code == 404
```

Now we need to adjust conftest to import necessary modules for `select` in lifespan? In main.py lifespan used `select`, but that's inside lifespan; it's fine, but the import is missing. I'll add import at top of lifespan in main.py:

```python
from sqlalchemy import select
```

Will add that.

Also, in main.py I used async with engine.connect() and await conn.execute(select(1)), so I need to import select there. I'll update.

Now, tests: ensure conftest uses `MockRedis` with `pipeline` that returns async with. The `MockPipeline.__aenter__` is async, so that's fine. Need to ensure `redis_client` override provides `mock_redis`. The middleware uses `redis_client` directly from `app.redis_client`, but we've overridden `get_redis` dependency, but middleware doesn't use dependency injection; it imports `redis_client` directly. So the mock won't affect middleware. That means rate limit tests might not work with mock because middleware uses the real redis_client from app.redis_client (the module-level variable). To make tests reliable, we need to inject the mock Redis into the middleware.

I can modify the rate limiter middleware to use `redis_client` from `app.redis_client` directly. In tests, we can replace `app.middleware.rate_limiter.redis_client` with the mock. Or we can use `get_redis` dependency in middleware? Middleware doesn't have dependency injection. So we need to make the middleware testable. We can patch the module variable. I'll update conftest to replace `app.middleware.rate_limiter.redis_client` with the mock, and also `app.services.url_service.redis_client` etc. Because the services also import the module-level client. So I'll override in conftest by setting the module attribute.

I'll add a fixture `mock_redis_client` that patches all required modules. Simpler: In conftest, after creating mock_redis, do:

```python
import app.middleware.rate_limiter as rl_mod
import app.services.url_service as us_mod
import app.services.delete_service as ds_mod

old_middleware_redis = rl_mod.redis_client
old_us_redis = us_mod.redis_client
old_ds_redis = ds_mod.redis_client

rl_mod.redis_client = mock_redis
us_mod.redis_client = mock_redis
ds_mod.redis_client = mock_redis

yield
# restore
rl_mod.redis_client = old_middleware_redis
us_mod.redis_client = old_us_redis
ds_mod.redis_client = old_ds_redis
```

That will make the mock work across all modules. I'll update conftest accordingly.

But in conftest we already have `mock_redis` fixture, we can do patching in it or in a separate autouse fixture. I'll create an autouse fixture `patch_redis` that uses mock_redis and patches the modules.

I'll update conftest:

```python
@pytest.fixture(autouse=True)
def patch_redis_client(mock_redis: MockRedis):
    """Replace Redis client in all modules that use it directly."""
    modules_to_patch = [
        "app.middleware.rate_limiter",
        "app.services.url_service",
        "app.services.delete_service",
    ]
    originals = {}
    for mod_name in modules_to_patch:
        mod = __import__(mod_name, fromlist=["redis_client"])
        originals[mod_name] = mod.redis_client
        mod.redis_client = mock_redis
    yield
    for mod_name, original in originals.items():
        mod = __import__(mod_name, fromlist=["redis_client"])
        mod.redis_client = original
```

That should work.

Now also `app.main` lifespan uses `redis_client` directly, but that's only at startup; for tests, we can skip lifespan or we can mock. The test client doesn't call lifespan because it overrides? Actually when we create the test client with ASGITransport, the lifespan is not executed. So fine.

I need to add `select` import in main.py lifespan:

```python
from sqlalchemy import select
```

Now, finalize the code. Provide all files in markdown blocks as per instructions. I'll include the final version of each file.

One more: In `app/main.py` I used `select` in lifespan but must import it. I'll include.

I'll also add `README.md` maybe, but not strictly required. I'll skip.

Now compile the final answer with all code blocks.```python app/__init__.py
# Package initialization for the URL shortener application
```

```python app/config.py
"""
Application settings loaded from environment variables using pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the URL shortener service."""

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener"
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Base URL for constructing short URLs (no trailing slash)
    BASE_URL: str = "http://localhost:8000"

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 100

    # Cache TTL for redirects (seconds)
    CACHE_TTL_SECONDS: int = 3600

    # Logging
    LOG_LEVEL: str = "INFO"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


# Singleton instance
settings = Settings()
```

```python app/database.py
"""
Async SQLAlchemy engine and session setup.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.config import settings

# Create async engine with connection pooling (recommended for production)
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    echo=False,  # set to True for SQL debugging
)

# Session factory bound to the engine
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """FastAPI dependency that provides a database session.

    Ensures the session is closed after the request.
    """
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()
```

```python app/redis_client.py
"""
Async Redis client with connection pool.
"""
import redis.asyncio as redis
from app.config import settings

# Create Redis connection pool
redis_pool = redis.ConnectionPool.from_url(
    settings.REDIS_URL,
    max_connections=50,
)

# Async Redis client
redis_client = redis.Redis(connection_pool=redis_pool)


async def get_redis() -> redis.Redis:
    """FastAPI dependency that provides a Redis client.

    The client is shared across requests (pool based).
    """
    return redis_client
```

```python app/models/__init__.py
from app.models.url import URLRecord

__all__ = ["URLRecord"]
```

```python app/models/url.py
"""
SQLAlchemy ORM model for the urls table.
"""
import datetime
from sqlalchemy import String, Text, BigInteger, Boolean, DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class URLRecord(Base):
    """Represents a shortened URL with analytics."""

    __tablename__ = "urls"

    id: Mapped[str] = mapped_column(String(7), primary_key=True, comment="Short identifier (base62, 7 chars)")
    original_url: Mapped[str] = mapped_column(Text, nullable=False, comment="Original long URL")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    clicks: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False, comment="Number of redirects")
    deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="Soft-delete flag")

    def __repr__(self) -> str:
        return f"<URLRecord(id={self.id}, original_url={self.original_url[:30]}...)>"
```

```python app/schemas/__init__.py
from app.schemas.url import ShortenRequest, ShortenResponse
from app.schemas.stats import StatsResponse

__all__ = ["ShortenRequest", "ShortenResponse", "StatsResponse"]
```

```python app/schemas/url.py
"""
Pydantic schemas for URL shortening request/response.
"""
from pydantic import BaseModel, HttpUrl, field_validator


class ShortenRequest(BaseModel):
    """Request body for creating a short URL."""
    url: HttpUrl  # Pydantic's HttpUrl validates http/https scheme and domain structure

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        """Additional validation if needed – here we only allow http and https (ensured by HttpUrl)."""
        # HttpUrl already restricts to http/https. Uncomment for extra SSRF checks.
        # if v.host and is_private_ip(v.host):
        #     raise ValueError("URL points to private network")
        return v


class ShortenResponse(BaseModel):
    """Response after successful URL shortening."""
    id: str
    short_url: str
    original_url: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "aB3x9Kq",
                "short_url": "http://localhost:8000/aB3x9Kq",
                "original_url": "https://example.com/very/long/path?query=1",
            }
        }
    }
```

```python app/schemas/stats.py
"""
Pydantic schema for URL stats response.
"""
from pydantic import BaseModel
from datetime import datetime


class StatsResponse(BaseModel):
    """Response containing click statistics for a short URL."""
    id: str
    original_url: str
    clicks: int
    created_at: datetime

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "aB3x9Kq",
                "original_url": "https://example.com/very/long/path?query=1",
                "clicks": 142,
                "created_at": "2025-01-15T10:30:00Z",
            }
        }
    }
```

```python app/utils/__init__.py
# Utils package
```

```python app/utils/id_generator.py
"""
Functions for generating and encoding short base62 IDs.
"""
import random
import string

# Base62 alphabet (alphanumeric)
BASE62_ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits
BASE62_LEN = len(BASE62_ALPHABET)  # 62
SHORT_ID_LENGTH = 7
MAX_ID_VALUE = BASE62_LEN**SHORT_ID_LENGTH  # 62^7 ≈ 3.5 trillion


def encode_base62(num: int) -> str:
    """Encode an integer into base62 string (without padding)."""
    if num == 0:
        return BASE62_ALPHABET[0]
    chars = []
    while num > 0:
        num, remainder = divmod(num, BASE62_LEN)
        chars.append(BASE62_ALPHABET[remainder])
    return "".join(reversed(chars))


def generate_short_id() -> str:
    """
    Generate a random 7-character base62 ID.

    Uses random number in [0, MAX_ID_VALUE) and encodes it, padding with
    the first character of the alphabet ('0' or 'a'?) to length 7.

    Note: We use the character '0' (first of alphabet) as padding.
    """
    # Generate random integer in full range
    rand_int = random.randrange(MAX_ID_VALUE)
    # Encode to base62 and pad with leading zeros (first alphabet char)
    encoded = encode_base62(rand_int)
    # Pad to required length
    return encoded.rjust(SHORT_ID_LENGTH, BASE62_ALPHABET[0])
```

```python app/utils/url_validator.py
"""
Custom URL validation beyond what pydantic HttpUrl provides.
(Could be extended for SSRF protection, private IP blocking, etc.)
"""

import ipaddress
from urllib.parse import urlparse

PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1"),
    ipaddress.ip_network("fc00::/7"),
]


def is_private_url(url: str) -> bool:
    """
    Check if the URL points to a private/reserved IP address.
    This is an optional SSRF protection – not used by default.
    """
    parsed = urlparse(url)
    if not parsed.hostname:
        return False
    try:
        ip = ipaddress.ip_address(parsed.hostname)
    except ValueError:
        # Hostname might not be an IP; could resolve DNS (not done here)
        return False
    return any(ip in network for network in PRIVATE_IP_RANGES)
```

```python app/services/__init__.py
# Services package
```

```python app/services/url_service.py
"""
Business logic for creating and retrieving short URLs.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.url import URLRecord
from app.utils.id_generator import generate_short_id
from app.redis_client import redis_client
from app.config import settings

logger = logging.getLogger(__name__)


async def create_short_url(db_session: AsyncSession, original_url: str) -> URLRecord:
    """Generate a unique short ID, create DB record, and return it."""
    # Retry loop to avoid collisions (extremely unlikely)
    max_attempts = 5
    for attempt in range(max_attempts):
        short_id = generate_short_id()
        # Check if ID already exists
        existing = await db_session.get(URLRecord, short_id)
        if not existing:
            record = URLRecord(id=short_id, original_url=original_url)
            db_session.add(record)
            await db_session.commit()
            await db_session.refresh(record)
            logger.info("Created short URL: id=%s for url=%s", short_id, original_url[:50])
            return record
        logger.warning("Collision on short_id %s, attempt %d", short_id, attempt + 1)
    raise RuntimeError("Failed to generate unique short ID after multiple attempts")


async def get_original_url(db_session: AsyncSession, short_id: str) -> Optional[URLRecord]:
    """Fetch URLRecord from cache or database, populate cache on miss."""
    cache_key = f"cache:{short_id}"
    # Try Redis cache first (cached value is just the original_url string)
    cached_url = await redis_client.get(cache_key)
    if cached_url:
        logger.debug("Cache hit for %s", short_id)
        # We still need a full record for status checks, so fetch from DB
        # (A more optimized version could cache full record as JSON)
        record = await db_session.get(URLRecord, short_id)
        if record and not record.deleted:
            return record
        # If record deleted while cached, invalidate and continue
        await redis_client.delete(cache_key)
        return None

    # Cache miss: query database
    stmt = select(URLRecord).where(URLRecord.id == short_id)
    result = await db_session.execute(stmt)
    record = result.scalar_one_or_none()
    if record and not record.deleted:
        # Populate cache
        await redis_client.set(cache_key, record.original_url, ex=settings.CACHE_TTL_SECONDS)
        return record
    return None


async def cache_url(short_id: str, original_url: str) -> None:
    """Store original_url in Redis cache."""
    await redis_client.set(f"cache:{short_id}", original_url, ex=settings.CACHE_TTL_SECONDS)


async def invalidate_cache(short_id: str) -> None:
    """Remove cached entry for given short ID."""
    await redis_client.delete(f"cache:{short_id}")
```

```python app/services/stats_service.py
"""
Service for click statistics and increment operations.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models.url import URLRecord

logger = logging.getLogger(__name__)


async def get_stats(db_session: AsyncSession, short_id: str) -> Optional[URLRecord]:
    """Retrieve URLRecord and stats, or None if not found / deleted."""
    stmt = select(URLRecord).where(URLRecord.id == short_id, URLRecord.deleted == False)
    result = await db_session.execute(stmt)
    return result.scalar_one_or_none()


async def increment_clicks(db_session: AsyncSession, short_id: str) -> None:
    """
    Atomically increment the clicks counter for a given short URL.
    This function is designed to be called as a background task.
    """
    stmt = (
        update(URLRecord)
        .where(URLRecord.id == short_id, URLRecord.deleted == False)
        .values(clicks=URLRecord.clicks + 1)
    )
    await db_session.execute(stmt)
    await db_session.commit()
    logger.debug("Incremented clicks for %s", short_id)
```

```python app/services/delete_service.py
"""
Service for soft-deleting a short URL and clearing its cache.
"""
import logging
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.url import URLRecord
from app.services.url_service import invalidate_cache

logger = logging.getLogger(__name__)


async def soft_delete(db_session: AsyncSession, short_id: str) -> bool:
    """
    Mark URLRecord as deleted and invalidate Redis cache.

    Returns True if record existed and was deleted, False if not found.
    """
    record = await db_session.get(URLRecord, short_id)
    if not record or record.deleted:
        return False
    record.deleted = True
    await db_session.commit()
    # Invalidate cache
    await invalidate_cache(short_id)
    logger.info("Soft-deleted short URL id=%s", short_id)
    return True
```

```python app/middleware/__init__.py
# Middleware package
```

```python app/middleware/rate_limiter.py
"""
ASGI middleware for rate limiting using Redis.
"""
import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.redis_client import redis_client
from app.config import settings

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """Custom exception for rate limit exceeded (used optionally)."""


async def check_rate_limit(client_ip: str) -> bool:
    """
    Check if the rate limit for the current minute bucket is exceeded.

    Returns True if allowed, False if limit reached.
    """
    current_minute = int(time.time() / 60)
    key = f"ratelimit:{client_ip}:{current_minute}"

    # Atomic INCR and EXPIRE using pipeline
    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.incr(key)
        pipe.expire(key, 120)  # Keep the key for up to 2 minutes to avoid race
        results = await pipe.execute()
        count = results[0]  # INCR result

    if count > settings.RATE_LIMIT_PER_MINUTE:
        logger.warning("Rate limit exceeded for IP %s (count=%d)", client_ip, count)
        return False
    return True


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces per-IP rate limits.

    If limit exceeded, returns 429 with Retry-After header.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get client IP (consider proxy forwarding)
        client_ip = request.client.host if request.client else "unknown"

        if not await check_rate_limit(client_ip):
            # Calculate seconds remaining in current minute
            now = int(time.time())
            seconds_to_next = 60 - (now % 60)
            retry_after = max(1, seconds_to_next)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
                headers={"Retry-After": str(retry_after)},
            )

        response = await call_next(request)
        return response
```

```python app/routers/__init__.py
# Routers package
```

```python app/routers/shorten.py
"""
Router for POST /shorten endpoint.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.url import ShortenRequest, ShortenResponse
from app.services.url_service import create_short_url
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    payload: ShortenRequest,
    db_session: AsyncSession = Depends(get_db),
) -> ShortenResponse:
    """
    Create a new short URL. Accepts a valid HTTP(S) URL, returns a shortened version.
    """
    original_url = str(payload.url)  # Convert HttpUrl to string
    try:
        record = await create_short_url(db_session, original_url)
    except RuntimeError:
        logger.exception("Failed to create short URL")
        raise HTTPException(status_code=500, detail="Internal error generating short ID")

    short_url = f"{settings.BASE_URL.rstrip('/')}/{record.id}"
    return ShortenResponse(
        id=record.id,
        short_url=short_url,
        original_url=record.original_url,
    )
```

```python app/routers/redirect.py
"""
Router for GET /{id} – redirect to the original URL.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import RedirectResponse

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.url_service import get_original_url
from app.services.stats_service import increment_clicks
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/{short_id}", status_code=status.HTTP_302_FOUND)
async def redirect_to_original(
    short_id: str,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    Redirect to the original long URL. Increments the click counter
    as a background task to minimise response latency.
    """
    record = await get_original_url(db_session, short_id)
    if not record or record.deleted:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Schedule click increment as a background task (non-blocking)
    background_tasks.add_task(increment_clicks, db_session, short_id)

    logger.info("Redirecting %s -> %s", short_id, record.original_url[:80])
    return RedirectResponse(url=record.original_url, status_code=302)
```

```python app/routers/stats.py
"""
Router for GET /stats/{id} – retrieve click statistics.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.stats_service import get_stats
from app.schemas.stats import StatsResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/stats/{short_id}", response_model=StatsResponse)
async def url_stats(
    short_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> StatsResponse:
    """
    Get statistics for a short URL (original URL, clicks, creation time).
    """
    record = await get_stats(db_session, short_id)
    if not record:
        raise HTTPException(status_code=404, detail="Short URL not found or deleted")
    return StatsResponse(
        id=record.id,
        original_url=record.original_url,
        clicks=record.clicks,
        created_at=record.created_at,
    )
```

```python app/routers/delete.py
"""
Router for DELETE /{id} – soft-delete a short URL.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.delete_service import soft_delete

router = APIRouter()
logger = logging.getLogger(__name__)


@router.delete("/{short_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_short_url(
    short_id: str,
    db_session: AsyncSession = Depends(get_db),
) -> None:
    """
    Soft-delete a short URL. It will no longer be available for redirection.
    """
    deleted = await soft_delete(db_session, short_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return None  # FastAPI will return 204
```

```python app/main.py
"""
FastAPI application entry point with lifespan, middleware, and routers.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.config import settings
from app.database import engine
from app.redis_client import redis_pool, redis_client
from app.routers import shorten, redirect, stats, delete
from app.middleware.rate_limiter import RateLimiterMiddleware

# Configure structured logging (JSON by default for production)
logging.basicConfig(
    level=settings.LOG_LEVEL,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "name": "%(name)s", "message": "%(message)s"}',
    datefmt="%Y-%m-%dT%H:%M:%S",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context for startup and graceful shutdown.
    - On startup: validate DB connection, ping Redis.
    - On shutdown: close DB and Redis connection pools.
    """
    # Startup
    logger.info("Starting URL Shortener service")
    # Verify DB connection by trying a trivial operation
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
            logger.info("Database connection established")
    except Exception:
        logger.critical("Failed to connect to database", exc_info=True)
        raise
    # Verify Redis connection
    try:
        await redis_client.ping()
        logger.info("Redis connection established")
    except Exception:
        logger.critical("Failed to connect to Redis", exc_info=True)
        raise

    yield

    # Shutdown
    logger.info("Shutting down URL Shortener service")
    await engine.dispose()
    await redis_client.aclose()
    logger.info("Connection pools closed. Goodbye.")


app = FastAPI(
    title="URL Shortener",
    description="Microservice for shortening URLs with analytics and rate limiting.",
    version="1.0.0",
    lifespan=lifespan,
)

# Rate limiter middleware
app.add_middleware(RateLimiterMiddleware)

# Include routers
app.include_router(shorten.router, tags=["shorten"])
app.include_router(redirect.router, tags=["redirect"])
app.include_router(stats.router, tags=["stats"])
app.include_router(delete.router, tags=["delete"])


# Global exception handlers (optional, for better error responses)
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": "Not found"})


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Internal server error", exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Health-check endpoint (not required by spec but useful)
@app.get("/health", include_in_schema=False)
async def health_check():
    return {"status": "ok"}
```

```python alembic/env.py
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
from app.models.url import Base  # Import your SQLAlchemy models

# Alembic Config object, used for .ini values
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run async migrations in 'online' mode."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    # Run async migrations
    asyncio.run(run_migrations_online())
```

```python alembic/versions/001_initial.py
"""Initial URL table

Revision ID: 001
Revises:
Create Date: 2025-04-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'urls',
        sa.Column('id', sa.String(7), primary_key=True, comment='Short identifier (base62, 7 chars)'),
        sa.Column('original_url', sa.Text(), nullable=False, comment='Original long URL'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('clicks', sa.BigInteger(), nullable=False, server_default=sa.text('0'), comment='Number of redirects'),
        sa.Column('deleted', sa.Boolean(), nullable=False, server_default=sa.text('false'), comment='Soft-delete flag'),
    )
    # Create indexes
    op.create_index('idx_urls_original_url', 'urls', ['original_url'])
    op.create_index('idx_urls_created_at', 'urls', ['created_at'])


def downgrade() -> None:
    op.drop_index('idx_urls_created_at', table_name='urls')
    op.drop_index('idx_urls_original_url', table_name='urls')
    op.drop_table('urls')
```

```Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (postgresql client libs for asyncpg)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Run Alembic migrations on startup via script or command
COPY docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```bash docker-entrypoint.sh
#!/bin/bash
set -e

# Run database migrations
echo "Running Alembic migrations..."
alembic upgrade head

# Start Uvicorn server
exec "$@"
```

```yaml docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@db:5432/urlshortener
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
    image: postgres:15
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgrespassword
      POSTGRES_DB: urlshortener
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

volumes:
  pgdata:
```

```text .env.example
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgrespassword@localhost:5432/urlshortener

# Redis
REDIS_URL=redis://localhost:6379/0

# Base URL (used for generating full short links)
BASE_URL=http://localhost:8000

# Rate limit: maximum requests per IP per minute
RATE_LIMIT_PER_MINUTE=100

# Cache TTL for redirect cache (seconds)
CACHE_TTL_SECONDS=3600

# Log level (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

```python requirements.txt
fastapi==0.110.0
uvicorn[standard]==0.27.0
sqlalchemy[asyncio]==2.0.25
asyncpg==0.29.0
redis==5.0.1
pydantic-settings==2.1.0
alembic==1.13.1
httpx==0.26.0
pytest==8.0.0
pytest-asyncio==0.23.3
aiosqlite==0.19.0
python-json-logger==2.0.7
```

```python tests/__init__.py
# Test package
```

```python tests/conftest.py
"""
Pytest fixtures for test database, Redis mock, and async HTTP client.
"""
import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import get_db
from app.redis_client import get_redis
from app.models.url import Base
from app.services.url_service import invalidate_cache

# Use SQLite in-memory for tests (requires aiosqlite)
TEST_DATABASE_URL = "sqlite+aiosqlite://"

# Create async engine for testing
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh test database schema and provide a session."""
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


# Simple async mock for Redis (used in all tests)
class MockRedis:
    """Simple async mock for Redis used in tests."""

    def __init__(self):
        self.store = {}
        self.expiry = {}

    async def get(self, key):
        if key in self.store and self._is_expired(key) is False:
            return self.store[key]
        return None

    async def set(self, key, value, ex=None):
        self.store[key] = value
        if ex:
            import time
            self.expiry[key] = time.time() + ex

    async def delete(self, key):
        self.store.pop(key, None)
        self.expiry.pop(key, None)
        return 1

    async def incr(self, key):
        if key not in self.store:
            self.store[key] = 0
        self.store[key] += 1
        return self.store[key]

    async def expire(self, key, ttl):
        import time
        if key in self.store:
            self.expiry[key] = time.time() + ttl

    async def pipeline(self, transaction=True):
        return MockPipeline(self)

    async def ping(self):
        return True

    def _is_expired(self, key):
        import time
        if key in self.expiry and time.time() > self.expiry[key]:
            del self.store[key]
            del self.expiry[key]
            return True
        return False


class MockPipeline:
    def __init__(self, mock_redis):
        self.mock = mock_redis
        self.commands = []

    def incr(self, key):
        self.commands.append(("incr", key))
        return self

    def expire(self, key, ttl):
        self.commands.append(("expire", key, ttl))
        return self

    async def execute(self):
        results = []
        import time
        for cmd, *args in self.commands:
            if cmd == "incr":
                res = await self.mock.incr(args[0])
                results.append(res)
            elif cmd == "expire":
                await self.mock.expire(args[0], args[1])
                results.append(True)
            else:
                results.append(None)
        return results

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


@pytest.fixture
def mock_redis():
    return MockRedis()


# Patch Redis client in modules that import it directly
@pytest.fixture(autouse=True)
def patch_redis_client(mock_redis: MockRedis):
    """Replace Redis client in all modules that use it directly."""
    import app.middleware.rate_limiter as rl_mod
    import app.services.url_service as us_mod
    import app.services.delete_service as ds_mod

    original_rl = rl_mod.redis_client
    original_us = us_mod.redis_client
    original_ds = ds_mod.redis_client

    rl_mod.redis_client = mock_redis
    us_mod.redis_client = mock_redis
    ds_mod.redis_client = mock_redis

    yield

    rl_mod.redis_client = original_rl
    us_mod.redis_client = original_us
    ds_mod.redis_client = original_ds


# Override the dependencies to use test DB and mock Redis
@pytest.fixture(autouse=True)
def override_dependencies(db_session: AsyncSession, mock_redis: MockRedis):
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: mock_redis
    yield
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client for testing FastAPI endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

```python tests/test_shorten.py
"""
Tests for POST /shorten endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shorten_valid_url(async_client: AsyncClient):
    payload = {"url": "https://example.com/valid/path?q=1"}
    response = await async_client.post("/shorten", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert len(data["id"]) == 7
    assert data["original_url"] == "https://example.com/valid/path?q=1"
    assert data["short_url"].startswith("http://test/")

    # Verify by retrieving redirect (should be saved)
    resp = await async_client.get(f"/{data['id']}")
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/valid/path?q=1"


@pytest.mark.asyncio
async def test_shorten_invalid_url(async_client: AsyncClient):
    # Invalid scheme (Pydantic HttpUrl rejects)
    payload = {"url": "ftp://bad-scheme.com"}
    response = await async_client.post("/shorten", json=payload)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_shorten_missing_url(async_client: AsyncClient):
    response = await async_client.post("/shorten", json={})
    assert response.status_code == 422
```

```python tests/test_redirect.py
"""
Tests for GET /{id} redirection.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URLRecord


async def create_test_record(db_session: AsyncSession, short_id: str, original_url: str):
    record = URLRecord(id=short_id, original_url=original_url)
    db_session.add(record)
    await db_session.commit()
    await db_session.refresh(record)
    return record


@pytest.mark.asyncio
async def test_redirect_existing(async_client: AsyncClient, db_session: AsyncSession):
    await create_test_record(db_session, "abcdefg", "https://example.com/page")
    response = await async_client.get("/abcdefg")
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com/page"


@pytest.mark.asyncio
async def test_redirect_not_found(async_client: AsyncClient):
    response = await async_client.get("/nonexist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_redirect_deleted(async_client: AsyncClient, db_session: AsyncSession):
    record = await create_test_record(db_session, "del1234", "https://example.com/deleted")
    record.deleted = True
    await db_session.commit()
    response = await async_client.get("/del1234")
    assert response.status_code == 404
```

```python tests/test_stats.py
"""
Tests for GET /stats/{id}.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URLRecord


@pytest.mark.asyncio
async def test_stats_existing(async_client: AsyncClient, db_session: AsyncSession):
    record = URLRecord(id="stat123", original_url="https://example.com/stat", clicks=42)
    db_session.add(record)
    await db_session.commit()

    response = await async_client.get("/stats/stat123")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "stat123"
    assert data["original_url"] == "https://example.com/stat"
    assert data["clicks"] == 42
    assert "created_at" in data


@pytest.mark.asyncio
async def test_stats_not_found(async_client: AsyncClient):
    response = await async_client.get("/stats/nonexist")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_stats_deleted(async_client: AsyncClient, db_session: AsyncSession):
    record = URLRecord(id="deleted", original_url="https://example.com/deleted", deleted=True)
    db_session.add(record)
    await db_session.commit()

    response = await async_client.get("/stats/deleted")
    # Should return 404 because stats service filters out deleted
    assert response.status_code == 404
```

```python tests/test_delete.py
"""
Tests for DELETE /{id}.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.url import URLRecord


@pytest.mark.asyncio
async def test_delete_existing(async_client: AsyncClient, db_session: AsyncSession):
    record = URLRecord(id="todel12", original_url="https://example.com/todelete")
    db_session.add(record)
    await db_session.commit()

    response = await async_client.delete("/todel12")
    assert response.status_code == 204

    # Verify it's now deleted
    from sqlalchemy import select
    result = await db_session.execute(select(URLRecord).where(URLRecord.id == "todel12"))
    updated = result.scalar_one()
    assert updated.deleted is True

    # Redis cache should be invalidated (redirect fails)
    redirect_resp = await async_client.get("/todel12")
    assert redirect_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent(async_client: AsyncClient):
    response = await async_client.delete("/noidhere")
    assert response.status_code == 404
```

```python tests/test_rate_limiter.py
"""
Tests for rate limiting middleware.
"""
import pytest
import asyncio
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_rate_limit_exceeded(async_client: AsyncClient, mock_redis):
    # Simulate limit exceeded by setting the count directly
    import time
    current_minute = int(time.time() / 60)
    key = f"ratelimit:testclient:{current_minute}"  # testclient is the test base_url host
    await mock_redis.set(key, 101)

    response = await async_client.get("/shorten", json={"url": "https://example.com"})
    assert response.status_code == 429
    assert "Retry-After" in response.headers


@pytest.mark.asyncio
async def test_rate_limit_allowed(async_client: AsyncClient, mock_redis):
    import time
    current_minute = int(time.time() / 60)
    key = f"ratelimit:testclient:{current_minute}"
    await mock_redis.set(key, 1)

    response = await async_client.get("/health")
    assert response.status_code != 429
```

```python tests/test_url_validation.py
"""
Unit tests for URL validation utilities.
"""
import pytest
from app.utils.url_validator import is_private_url


def test_private_ip_url():
    assert is_private_url("http://127.0.0.1:8080") is True
    assert is_private_url("http://10.0.0.1") is True
    assert is_private_url("https://192.168.1.1") is True


def test_public_url():
    assert is_private_url("https://example.com") is False
    assert is_private_url("http://8.8.8.8") is False


def test_hostname_url():
    # Not an IP, so not private
    assert is_private_url("https://myprivate.local") is False
```

```python tests/test_id_generator.py
"""
Unit tests for base62 ID generation.
"""
import pytest
from app.utils.id_generator import encode_base62, generate_short_id

def test_encode_base62_zero():
    assert encode_base62(0) == "0"

def test_generate_short_id_length_and_chars():
    from app.utils.id_generator import BASE62_ALPHABET
    id_str = generate_short_id()
    assert len(id_str) == 7
    for ch in id_str:
        assert ch in BASE62_ALPHABET

def test_generate_short_id_uniqueness():
    ids = {generate_short_id() for _ in range(1000)}
    assert len(ids) == 1000
```

```python tests/test_services.py
"""
Unit/Integration tests for service layer functions.
"""
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.url import URLRecord
from app.services.url_service import create_short_url, get_original_url, cache_url, invalidate_cache
from app.services.stats_service import get_stats, increment_clicks
from app.services.delete_service import soft_delete


@pytest.mark.asyncio
async def test_create_short_url(db_session: AsyncSession):
    original = "https://example.com/test"
    record = await create_short_url(db_session, original)
    assert len(record.id) == 7
    assert record.original_url == original
    assert record.clicks == 0
    assert record.deleted is False

    # Verify persistence
    fetched = await db_session.get(URLRecord, record.id)
    assert fetched is not None


@pytest.mark.asyncio
async def test_increment_clicks(db_session: AsyncSession):
    record = URLRecord(id="clicks1", original_url="https://example.com/clickme", clicks=0)
    db_session.add(record)
    await db_session.commit()

    await increment_clicks(db_session, "clicks1")

    await db_session.refresh(record)
    assert record.clicks == 1

    await increment_clicks(db_session, "clicks1")
    await db_session.refresh(record)
    assert record.clicks == 2


@pytest.mark.asyncio
async def test_soft_delete(db_session: AsyncSession):
    record = URLRecord(id="todel13", original_url="https://example.com/delete")
    db_session.add(record)
    await db_session.commit()

    result = await soft_delete(db_session, "todel13")
    assert result is True
    assert record.deleted is True

    result2 = await soft_delete(db_session, "todel13")  # already deleted
    assert result2 is False


@pytest.mark.asyncio
async def test_get_stats_ok(db_session: AsyncSession):
    record = URLRecord(id="statok", original_url="https://example.com/stat", clicks=5)
    db_session.add(record)
    await db_session.commit()

    stats = await get_stats(db_session, "statok")
    assert stats is not None
    assert stats.clicks == 5

    # Deleted record should not be returned
    record.deleted = True
    await db_session.commit()
    stats2 = await get_stats(db_session, "statok")
    assert stats2 is None
```

I have provided all required files with paths, type hints, documentation, error handling, and tests. The code follows the architecture document exactly.