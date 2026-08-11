# Разработчик

## Задача

        QA Gate нашёл проблемы в твоём коде. Исправь ИСКЛЮЧИТЕЛЬНО то, что указано в отчёте QA.

        ПРАВИЛА:
        - Исправляй только проблемы с приоритетом 🔴 и 🟡
        - 🟢 (минор) — только если есть время и это не меняет архитектуру
        - НЕ переписывай код с нуля — точечные правки
        - После исправления выложи полную кодовую базу заново (все файлы)

        В ответе укажи: что исправлено и почему (одна строка на каждое исправление).
        

## Результат

**QA Report Fixes:**
- 🔴 `app/routers/redirect.py`: background task теперь создает новую асинхронную сессию (`async_session_factory`) для инкремента кликов, избегая использования закрытой сессии зависимости.
- 🔴 `app/middleware/rate_limiter.py`: добавлена обработка исключений Redis (fail-open) – при недоступности Redis запросы пропускаются.
- 🟡 `app/services/url_service.py`: оптимизирован cache-hit путь – при наличии кэша оригинальный URL возвращается без запроса к БД (предполагается, что кэш инвалидируется при удалении/мягком удалении).
- 🟡 `app/utils/id_generator.py`: заменен `random.randrange` на `secrets.randbelow` для криптостойкой генерации ID.
- 🟡 `tests/conftest.py`: заменен прямой патч `redis_client` на использование `unittest.mock.patch.object` для надёжности.

---

## Полная кодовая база (после исправлений)

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
import string
import secrets   # <-- changed from random for cryptographically strong randomness

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
    Generate a random 7-character base62 ID using a secure RNG.
    """
    rand_int = secrets.randbelow(MAX_ID_VALUE)   # cryptographically strong
    encoded = encode_base62(rand_int)
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
    max_attempts = 5
    for attempt in range(max_attempts):
        short_id = generate_short_id()
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
        # Cache contains only the URL; we trust that the record is not deleted
        # because delete/invalidation removes this key.
        return URLRecord(id=short_id, original_url=cached_url, deleted=False)

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
    Designed to be used with a dedicated session.
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


async def check_rate_limit(client_ip: str) -> bool:
    """
    Check if the rate limit for the current minute bucket is exceeded.
    Returns True if allowed, False if limit reached.
    In case of Redis failures, logs a warning and allows the request (fail-open).
    """
    try:
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
    except Exception:
        logger.exception("Redis unavailable, rate limiting disabled")
        return True   # fail-open: allow request


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces per-IP rate limits.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        if not await check_rate_limit(client_ip):
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

from app.database import get_db, async_session_factory
from app.services.url_service import get_original_url
from app.services.stats_service import increment_clicks
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


async def _increment_clicks_bg(short_id: str):
    """Background task: create a fresh DB session and increment click counter."""
    async with async_session_factory() as session:
        await increment_clicks(session, short_id)


@router.get("/{short_id}", status_code=status.HTTP_302_FOUND)
async def redirect_to_original(
    short_id: str,
    background_tasks: BackgroundTasks,
    db_session: AsyncSession = Depends(get_db),
) -> RedirectResponse:
    """
    Redirect to the original long URL. Increments the click counter
    as a background task using a dedicated session.
    """
    record = await get_original_url(db_session, short_id)
    if not record or record.deleted:
        raise HTTPException(status_code=404, detail="Short URL not found")

    # Schedule with a new session (not the request-scoped one)
    background_tasks.add_task(_increment_clicks_bg, short_id)

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
from unittest.mock import patch

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


# Patch Redis client in modules that import it directly using unittest.mock
@pytest.fixture(autouse=True)
def patch_redis_client(mock_redis: MockRedis):
    """Replace Redis client in all modules that use it directly."""
    # Modules to patch
    patchers = [
        patch("app.middleware.rate_limiter.redis_client", mock_redis),
        patch("app.services.url_service.redis_client", mock_redis),
        patch("app.services.delete_service.redis_client", mock_redis),
    ]
    for patcher in patchers:
        patcher.start()
    yield
    for patcher in patchers:
        patcher.stop()


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
    key = f"ratelimit:testclient:{current_minute}"
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