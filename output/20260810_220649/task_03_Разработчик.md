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

```python
# requirements.txt
fastapi==0.110.0
uvicorn[standard]==0.27.0
sqlalchemy[asyncio]==2.0.27
asyncpg==0.29.0
redis[hiredis]==5.0.1
pydantic==2.6.0
pydantic-settings==2.1.0
alembic==1.13.1
loguru==0.7.2
python-dotenv==1.0.1
```

```python
# requirements-dev.txt
-r requirements.txt
pytest==7.4.3
pytest-asyncio==0.23.3
httpx==0.27.0
flake8==7.0.0
mypy==1.8.0
```

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = "tests"

[tool.mypy]
python_version = "3.11"
ignore_missing_imports = true
strict = true

[tool.flake8]
max-line-length = 100
extend-ignore = "E203,W503"
```

```text
# .env.example
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/urlshortener
REDIS_URL=redis://localhost:6379/0
BASE_URL=https://short.example.com
RATE_LIMIT_PER_MINUTE=100
CACHE_TTL_SECONDS=3600
SHORT_ID_LENGTH=7
UVICORN_WORKERS=4
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
```

```yaml
# docker/docker-compose.yml
version: "3.8"

services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: urlshortener
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    env_file:
      - ../.env
    environment:
      DATABASE_URL: postgresql+asyncpg://user:pass@postgres:5432/urlshortener
      REDIS_URL: redis://redis:6379/0
      UVICORN_HOST: "0.0.0.0"
      UVICORN_PORT: "8000"
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis

volumes:
  pgdata:
```

```dockerfile
# docker/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

```python
# alembic/env.py
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.config import settings
from app.models.url import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the main configuration option to the URL
config.set_main_option("sqlalchemy.url", settings.database_url)

# add your model's MetaData object here for 'autogenerate' support
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

def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context."""
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

```ini
# alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = driver://user:pass@localhost/dbname

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

```python
# alembic/versions/001_initial_urls.py
"""initial urls table

Revision ID: 001
Revises:
Create Date: 2025-01-15 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'urls',
        sa.Column('id', sa.UUID(), nullable=False, primary_key=True),
        sa.Column('short_id', sa.String(7), nullable=False),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('TRUE')),
        sa.Column('click_count', sa.BigInteger(), nullable=False, server_default=sa.text('0')),
        sa.Column('last_accessed_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_unique_index('idx_urls_short_id', 'urls', ['short_id'])
    op.create_index('idx_urls_active', 'urls', ['short_id'], postgresql_where=sa.text('is_active = TRUE'))


def downgrade() -> None:
    op.drop_index('idx_urls_active', table_name='urls')
    op.drop_index('idx_urls_short_id', table_name='urls')
    op.drop_table('urls')
```

```python
# app/__init__.py
# URL Shortener application package
```

```python
# app/main.py
"""
FastAPI application entry point.
Initializes routers, middleware, and lifespan events.
"""
import asyncio
import contextlib
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.health import router as health_router
from app.api.v1.router import router as v1_router
from app.config import settings
from app.db.session import close_db, init_db
from app.db.redis_client import close_redis, get_redis
from app.middleware.rate_limit import RateLimitMiddleware
from app.tasks import background_tasks_set


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Lifespan context manager to initialize and shutdown resources.
    """
    logger.info("Starting application...")
    await init_db()
    try:
        await get_redis()  # ensure Redis is connected (pool created lazily)
    except Exception:
        logger.warning("Redis is not available, some features may be degraded.")
    yield
    logger.info("Shutting down...")
    # Wait for pending background tasks to finish
    if background_tasks_set:
        logger.info(f"Waiting for {len(background_tasks_set)} background tasks to complete")
        for task in asyncio.as_completed(background_tasks_set):
            try:
                await task
            except Exception:
                logger.exception("Background task failed during shutdown")
    await close_db()
    await close_redis()


def create_app() -> FastAPI:
    """
    Factory to create and configure the FastAPI application.
    """
    app = FastAPI(
        title="URL Shortener",
        description="A microservice to shorten URLs and track redirects.",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS (optional for development, adjust in production)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        redis_url=settings.redis_url,
        limit=settings.rate_limit_per_minute,
    )

    # Include routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(v1_router, prefix="/api/v1", tags=["v1"])

    return app


app = create_app()
```

```python
# app/config.py
"""
Application configuration via pydantic-settings.
Reads environment variables with .env support.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener"
    redis_url: str = "redis://localhost:6379/0"
    base_url: str = "https://short.example.com"
    rate_limit_per_minute: int = 100
    cache_ttl_seconds: int = 3600
    short_id_length: int = 7

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
```

```python
# app/dependencies.py
"""
Dependency injection for database sessions and Redis connections.
"""
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import SessionLocal  # sessionmaker
from app.db.redis_client import get_redis as _get_redis


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    Yields an async database session and ensures rollback on errors.
    """
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


# For convenience, re-export redis as a dependency
# (Redis client is a singleton pool, not a per-request connection)
async def get_redis_client():
    return await _get_redis()
```

```python
# app/tasks.py
"""
Background task management.
Stores references to background tasks so they can be awaited during shutdown.
"""
import asyncio
from typing import Set

background_tasks_set: Set[asyncio.Task] = set()


def add_background_task(coro):
    """Schedule a coroutine as a background task and keep a reference."""
    task = asyncio.create_task(coro)
    background_tasks_set.add(task)
    task.add_done_callback(background_tasks_set.discard)
    return task
```

```python
# app/api/__init__.py
```

```python
# app/api/health.py
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    Verifies DB and Redis connectivity via their dependencies.
    """
    # In a real scenario we'd check connectivity here.
    # For simplicity, we just assume they are working.
    return {"status": "ok"}
```

```python
# app/api/v1/__init__.py
```

```python
# app/api/v1/router.py
from fastapi import APIRouter
from app.api.v1.shorten import router as shorten_router
from app.api.v1.redirect import router as redirect_router
from app.api.v1.stats import router as stats_router
from app.api.v1.delete import router as delete_router

router = APIRouter()
router.include_router(shorten_router, prefix="/shorten", tags=["Shorten"])
router.include_router(redirect_router, tags=["Redirect"])
router.include_router(stats_router, prefix="/stats", tags=["Stats"])
router.include_router(delete_router, tags=["Delete"])
```

```python
# app/api/v1/shorten.py
"""
POST /shorten endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.schemas.shorten import ShortenRequest, ShortenResponse
from app.services.url_service import UrlService
from app.core.url_validator import validate_url

router = APIRouter()


@router.post("", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    payload: ShortenRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a shortened URL.
    Validates the input URL, generates a short ID, stores it, and returns the short URL.
    """
    # Validate URL (SSRF, scheme, length)
    try:
        validated_url = validate_url(payload.url)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    service = UrlService(db)
    try:
        result = await service.create_short_url(
            original_url=validated_url,
            expires_at=payload.expires_at,
        )
    except RuntimeError as e:
        # Exceeded retry attempts for short_id generation
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not generate unique short ID. Please try again.",
        )

    return result
```

```python
# app/api/v1/redirect.py
"""
GET /{short_id} redirect endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, status, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis_client
from app.services.url_service import UrlService
from app.services.cache_service import CacheService
from app.tasks import add_background_task

router = APIRouter()


@router.get("/{short_id}")
async def redirect_to_original(
    short_id: str = Path(..., min_length=1, max_length=7, regex=r'^[a-zA-Z0-9]+$'),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    """
    Redirect to the original URL using the short ID.
    Checks cache first, then DB. Increments click counter and updates DB in background.
    """
    service = UrlService(db)
    cache = CacheService(redis)

    # Try cache
    cached_url = await cache.get_cached_url(short_id)
    if cached_url:
        # Increment counter in background
        add_background_task(service.increment_click_count(short_id))
        return Response(
            status_code=status.HTTP_302_FOUND,
            headers={"Location": cached_url},
        )

    # Fetch from DB
    url_obj = await service.get_url(short_id)
    if url_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    if not url_obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    if url_obj.expires_at is not None and url_obj.expires_at < service._now():
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="URL expired")

    # Store in cache for next time
    await cache.set_cached_url(short_id, url_obj.original_url)

    # Increment counter (background)
    add_background_task(service.increment_click_count(short_id))

    return Response(
        status_code=status.HTTP_302_FOUND,
        headers={"Location": url_obj.original_url},
    )
```

```python
# app/api/v1/stats.py
"""
GET /stats/{short_id} endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.services.url_service import UrlService
from app.schemas.stats import StatsResponse

router = APIRouter()


@router.get("/{short_id}", response_model=StatsResponse)
async def get_stats(
    short_id: str = Path(..., min_length=1, max_length=7, regex=r'^[a-zA-Z0-9]+$'),
    db: AsyncSession = Depends(get_db),
):
    """
    Return statistics for a shortened URL.
    """
    service = UrlService(db)
    url_obj = await service.get_url(short_id)
    if url_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    if not url_obj.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    return StatsResponse.model_validate(url_obj)
```

```python
# app/api/v1/delete.py
"""
DELETE /{short_id} endpoint (soft delete).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_redis_client
from app.services.url_service import UrlService
from app.services.cache_service import CacheService

router = APIRouter()


@router.delete("/{short_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    short_id: str = Path(..., min_length=1, max_length=7, regex=r'^[a-zA-Z0-9]+$'),
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis_client),
):
    """
    Soft-delete a shortened URL.
    """
    service = UrlService(db)
    cache = CacheService(redis)
    url_obj = await service.get_url(short_id)
    if url_obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    await service.soft_delete_url(short_id)
    # Invalidate cache
    await cache.invalidate_url(short_id)
    return None
```

```python
# app/core/__init__.py
```

```python
# app/core/short_id.py
"""
Short ID generator using Base62 encoding.
Generates a random 7-character string.
"""
import secrets
import string

BASE62_ALPHABET = string.ascii_letters + string.digits  # 62 chars
SHORT_ID_LENGTH = 7  # default, can be overridden


def generate_short_id(length: int = SHORT_ID_LENGTH) -> str:
    """
    Generate a cryptographically secure short ID from Base62 alphabet.
    Args:
        length: Number of characters (default 7)
    Returns:
        Random short_id string
    """
    return ''.join(secrets.choice(BASE62_ALPHABET) for _ in range(length))
```

```python
# app/core/url_validator.py
"""
URL validation with SSRF protection.
Only allows http/https schemes, rejects localhost and private IPs.
"""
import ipaddress
import re
from urllib.parse import urlparse

# List of blacklisted hostnames (case-insensitive)
BLACKLISTED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "[::1]",  # IPv6 loopback
}


def validate_url(url: str) -> str:
    """
    Validate and sanitize a URL.
    Raises ValueError if invalid.
    """
    if not url:
        raise ValueError("URL is required")
    if len(url) > 2048:
        raise ValueError("URL exceeds maximum length of 2048 characters")

    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError("Invalid URL format")
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only HTTP and HTTPS schemes are allowed")

    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Invalid hostname")

    # Check blacklist
    if hostname.lower() in BLACKLISTED_HOSTNAMES:
        raise ValueError("URL points to a forbidden address")

    # Check if hostname is an IP address in private/loopback ranges
    try:
        ip = ipaddress.ip_address(hostname)
    except ValueError:
        # Not an IP, skip address validation
        pass
    else:
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            raise ValueError("URL points to a private or reserved IP address")

    return url
```

```python
# app/core/rate_limiter.py
"""
Sliding window rate limiter using Redis Sorted Sets.
Implements a sliding window algorithm as required by architecture.
"""
import time
from typing import Optional

from redis.asyncio import Redis


class RateLimiter:
    """Rate limiter using sliding window (Redis sorted sets)."""

    def __init__(self, redis: Redis, limit: int = 100, window: int = 60):
        self.redis = redis
        self.limit = limit
        self.window = window

    async def is_rate_limited(self, client_ip: str) -> Optional[int]:
        """
        Check if client has exceeded the limit.
        Returns remaining requests if allowed, or None and sets Retry-After header time.
        Uses a sliding window: remove entries older than window, count current,
        and add new timestamp if allowed.
        """
        key = f"rate:{client_ip}"
        now = time.time()
        window_start = now - self.window

        # Remove entries outside the window and count current
        await self.redis.zremrangebyscore(key, 0, window_start)
        count = await self.redis.zcard(key)

        if count >= self.limit:
            # Find oldest timestamp to calculate Retry-After
            oldest = await self.redis.zrange(key, 0, 0, withscores=True)
            if oldest:
                retry_after = int(oldest[0][1] - window_start)
            else:
                retry_after = self.window
            return None  # blocked

        # Add current request timestamp
        await self.redis.zadd(key, {str(now): now})
        # Expire the key after window to auto-cleanup
        await self.redis.expire(key, self.window)

        remaining = self.limit - count - 1
        return remaining
```

```python
# app/middleware/__init__.py
```

```python
# app/middleware/rate_limit.py
"""
Rate limiting middleware for FastAPI.
Integrates RateLimiter and applies to all routes (except health maybe).
"""
from typing import Callable, Awaitable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.rate_limiter import RateLimiter
from app.db.redis_client import get_redis
from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to apply rate limiting using Redis."""

    def __init__(
        self,
        app,
        redis_url: str,
        limit: int = settings.rate_limit_per_minute,
        exclude_paths: set = None
    ):
        super().__init__(app)
        self.redis_url = redis_url
        self.limit = limit
        self.exclude_paths = exclude_paths or {"/health", "/docs", "/redoc", "/openapi.json"}

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        # Skip rate limiting for excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Safely extract client IP, with fallback
        client_ip = request.client.host if request.client and request.client.host else "unknown"
        redis = await get_redis()
        limiter = RateLimiter(redis, limit=self.limit)
        remaining = await limiter.is_rate_limited(client_ip)

        if remaining is None:
            # Rate limit exceeded
            return Response(
                content='{"detail":"Too many requests"}',
                status_code=429,
                media_type="application/json",
                headers={"Retry-After": "60"}
            )

        response: Response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
```

```python
# app/models/__init__.py
```

```python
# app/models/url.py
"""
SQLAlchemy model for the urls table.
"""
import uuid
from datetime import datetime

from sqlalchemy import String, Text, Boolean, BigInteger, TIMESTAMP, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class Url(Base):
    __tablename__ = "urls"

    id: Mapped[uuid.UUID] = mapped_column(UUID(), primary_key=True, default=uuid.uuid4)
    short_id: Mapped[str] = mapped_column(String(7), unique=True, nullable=False, index=True)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default='t')
    click_count: Mapped[int] = mapped_column(BigInteger, default=0, server_default='0')
    last_accessed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Url short_id={self.short_id!r}>"
```

```python
# app/schemas/__init__.py
```

```python
# app/schemas/shorten.py
"""
Pydantic schemas for shorten endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ShortenRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048, description="Original URL to shorten")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date in ISO format")


class ShortenResponse(BaseModel):
    short_id: str
    short_url: str
    original_url: str
    created_at: datetime

    class Config:
        from_attributes = True
```

```python
# app/schemas/stats.py
"""
Pydantic schemas for stats endpoint.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class StatsResponse(BaseModel):
    short_id: str
    original_url: str
    click_count: int
    created_at: datetime
    last_accessed_at: Optional[datetime]
    is_active: bool

    class Config:
        from_attributes = True
```

```python
# app/schemas/common.py
"""
Common error response schema.
"""
from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str
```

```python
# app/services/__init__.py
```

```python
# app/services/url_service.py
"""
Business logic for URL shortening, retrieval, stats, and deletion.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.config import settings
from app.core.short_id import generate_short_id
from app.models.url import Url


class UrlService:
    """Service handling all URL-related operations."""

    MAX_RETRIES = 5

    def __init__(self, session: AsyncSession):
        self.session = session

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    async def create_short_url(self, original_url: str, expires_at: Optional[datetime] = None) -> dict:
        """
        Create a new short URL record.
        Generates a unique short_id with retry on collision.
        Returns a dictionary suitable for ShortenResponse.
        """
        for attempt in range(self.MAX_RETRIES):
            short_id = generate_short_id(settings.short_id_length)
            # Check if it already exists (race condition possible, but we rely on unique constraint)
            exists = await self.session.execute(
                select(Url.short_id).where(Url.short_id == short_id)
            )
            if exists.scalar_one_or_none() is None:
                url_obj = Url(
                    id=uuid.uuid4(),
                    short_id=short_id,
                    original_url=original_url,
                    expires_at=expires_at,
                )
                self.session.add(url_obj)
                try:
                    await self.session.commit()
                except Exception:
                    await self.session.rollback()
                    if attempt < self.MAX_RETRIES - 1:
                        logger.warning(f"Collision on short_id {short_id}, retrying...")
                        continue
                    raise RuntimeError("Failed to create short URL after retries")
                await self.session.refresh(url_obj)
                return {
                    "short_id": url_obj.short_id,
                    "short_url": f"{settings.base_url}/{url_obj.short_id}",
                    "original_url": url_obj.original_url,
                    "created_at": url_obj.created_at,
                }
        raise RuntimeError("Exhausted retries for short ID generation")

    async def get_url(self, short_id: str) -> Optional[Url]:
        """
        Retrieve a URL object by short_id.
        """
        result = await self.session.execute(
            select(Url).where(Url.short_id == short_id)
        )
        return result.scalar_one_or_none()

    async def increment_click_count(self, short_id: str) -> None:
        """
        Increment click count and update last_accessed_at for a URL.
        This is intended to be called as a background task.
        Uses atomic update to avoid race conditions.
        """
        now = self._now()
        stmt = (
            update(Url)
            .where(Url.short_id == short_id)
            .values(
                click_count=Url.click_count + 1,
                last_accessed_at=now,
            )
        )
        await self.session.execute(stmt)
        try:
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            logger.error(f"Failed to increment click count for {short_id}")

    async def soft_delete_url(self, short_id: str) -> None:
        """
        Soft delete a URL by setting is_active=False.
        """
        stmt = (
            update(Url)
            .where(Url.short_id == short_id)
            .values(is_active=False)
        )
        await self.session.execute(stmt)
        await self.session.commit()
```

```python
# app/services/cache_service.py
"""
Redis cache service for URL redirects.
"""
from typing import Optional

from redis.asyncio import Redis

from app.config import settings


class CacheService:
    """Service for caching shortened URLs in Redis."""

    def __init__(self, redis: Redis):
        self.redis = redis

    def _cache_key(self, short_id: str) -> str:
        return f"url:{short_id}"

    async def get_cached_url(self, short_id: str) -> Optional[str]:
        """
        Get original URL from cache if present.
        """
        value = await self.redis.get(self._cache_key(short_id))
        if value is not None:
            return value.decode("utf-8")
        return None

    async def set_cached_url(self, short_id: str, original_url: str) -> None:
        """
        Store original URL in cache with TTL.
        """
        await self.redis.setex(
            self._cache_key(short_id),
            settings.cache_ttl_seconds,
            original_url,
        )

    async def invalidate_url(self, short_id: str) -> None:
        """
        Remove a cached URL (used on delete).
        """
        await self.redis.delete(self._cache_key(short_id))
```

```python
# app/db/__init__.py
```

```python
# app/db/session.py
"""
Database session and engine management using SQLAlchemy async.
"""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
)

# SessionLocal is a factory for sessions
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_db() -> None:
    """
    Initialize database engine (run on startup).
    """
    # The engine is created lazily; just verify connectivity
    async with engine.connect() as conn:
        await conn.execute(select(1))


async def close_db() -> None:
    """
    Dispose engine on shutdown.
    """
    await engine.dispose()
```

```python
# app/db/redis_client.py
"""
Redis connection management. Provides a singleton Redis client.
"""
import asyncio
from redis.asyncio import Redis

from app.config import settings

_redis: Redis | None = None
_lock = asyncio.Lock()


async def get_redis() -> Redis:
    """
    Return the Redis client, creating it if necessary.
    """
    global _redis
    if _redis is None:
        async with _lock:
            if _redis is None:
                _redis = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
                await _redis.ping()
    return _redis


async def close_redis() -> None:
    """
    Close the Redis connection.
    """
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
```

```python
# tests/__init__.py
```

```python
# tests/conftest.py
"""
Fixtures for testing: test client, test database, test Redis.
"""
import asyncio
import os
from typing import AsyncIterator, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from redis.asyncio import Redis

from app.main import create_app
from app.models.url import Base
from app.dependencies import get_db, get_redis_client

# Override settings for testing
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test.db"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"  # high to avoid interference in tests

from app.config import settings  # noqa: E402

# We'll use SQLite for database testing (requires aiosqlite)
# Install aiosqlite: pip install aiosqlite
# It's not in requirements.txt, but for tests we'll need it.
# We'll add a note in the README or we can include it in dev requirements.
# In the test file we'll assume it's installed.

TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create a test database engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
    # Delete file after tests
    if os.path.exists("./test.db"):
        os.remove("./test.db")


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncIterator[AsyncSession]:
    """Provide a transactional session for each test."""
    async with test_engine.connect() as conn:
        # Begin a transaction
        async with conn.begin():
            # Create a session bound to this connection
            session_maker = async_sessionmaker(conn, class_=AsyncSession, expire_on_commit=False)
            async with session_maker() as session:
                yield session
            # Rollback after test


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:
    """Provide a Redis client for tests."""
    r = Redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
    await r.flushdb()  # clean test db
    yield r
    await r.flushdb()
    await r.close()


@pytest_asyncio.fixture
async def app(test_engine, redis_client) -> AsyncIterator[AsyncClient]:
    """Create a test FastAPI app with overridden dependencies."""
    app = create_app()
    # Override dependencies to use test DB and Redis
    async def override_get_db():
        async with async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)() as session:
            try:
                yield session
            finally:
                await session.rollback()
                await session.close()

    async def override_get_redis():
        return redis_client

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
```

```python
# tests/test_short_id.py
import re
from app.core.short_id import generate_short_id

def test_generate_short_id_length():
    sid = generate_short_id(7)
    assert len(sid) == 7
    assert re.fullmatch(r'[a-zA-Z0-9]{7}', sid) is not None

def test_uniqueness():
    ids = {generate_short_id(7) for _ in range(100)}
    assert len(ids) == 100  # extremely unlikely to collide
```

```python
# tests/test_url_validation.py
import pytest
from app.core.url_validator import validate_url

valid_cases = [
    "http://example.com",
    "https://example.com/path?q=1",
    "https://sub.domain.example.com:8080/path",
]

invalid_cases = [
    ("", "URL is required"),
    ("ftp://example.com", "Only HTTP and HTTPS schemes are allowed"),
    ("http://localhost", "URL points to a forbidden address"),
    ("http://127.0.0.1", "URL points to a forbidden address"),
    ("http://0.0.0.0", "URL points to a forbidden address"),
    ("http://10.0.0.1", "URL points to a private or reserved IP address"),
    ("http://192.168.1.1", "URL points to a private or reserved IP address"),
    ("http://[::1]", "URL points to a forbidden address"),
    ("not a url", "Invalid URL format"),
    ("a"*2049 + "https://a.com", "URL exceeds maximum length"),
]

def test_valid_urls():
    for url in valid_cases:
        assert validate_url(url) == url

def test_invalid_urls():
    for url, expected_msg in invalid_cases:
        with pytest.raises(ValueError, match=expected_msg):
            validate_url(url)
```

```python
# tests/test_shorten.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_short_url(app: AsyncClient):
    payload = {"url": "https://example.com/very/long/path"}
    response = await app.post("/api/v1/shorten", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "short_id" in data
    assert data["original_url"] == payload["url"]
    assert data["short_url"].startswith("https://")

@pytest.mark.asyncio
async def test_invalid_url_rejection(app: AsyncClient):
    payload = {"url": "ftp://invalid"}
    response = await app.post("/api/v1/shorten", json=payload)
    assert response.status_code == 400
```

```python
# tests/test_redirect.py
import pytest
import datetime
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_redirect_success(app: AsyncClient):
    # First create a short URL
    payload = {"url": "https://example.com"}
    create_resp = await app.post("/api/v1/shorten", json=payload)
    assert create_resp.status_code == 201
    short_id = create_resp.json()["short_id"]

    # Redirect
    redirect_resp = await app.get(f"/api/v1/{short_id}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == payload["url"]

@pytest.mark.asyncio
async def test_redirect_not_found(app: AsyncClient):
    response = await app.get("/api/v1/nonexist", follow_redirects=False)
    assert response.status_code == 404

@pytest.mark.asyncio
async def test_redirect_expired(app: AsyncClient):
    # Create short URL with past expiry
    payload = {"url": "https://example.com", "expires_at": "2020-01-01T00:00:00Z"}
    create_resp = await app.post("/api/v1/shorten", json=payload)
    assert create_resp.status_code == 201
    short_id = create_resp.json()["short_id"]

    redirect_resp = await app.get(f"/api/v1/{short_id}", follow_redirects=False)
    assert redirect_resp.status_code == 410
```

```python
# tests/test_stats.py
import pytest
import asyncio
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_stats(app: AsyncClient):
    # Create short URL
    payload = {"url": "https://example.com"}
    create_resp = await app.post("/api/v1/shorten", json=payload)
    short_id = create_resp.json()["short_id"]

    # Get stats initially
    stats_resp = await app.get(f"/api/v1/stats/{short_id}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["short_id"] == short_id
    assert data["click_count"] == 0

@pytest.mark.asyncio
async def test_stats_after_redirect(app: AsyncClient):
    # Create short URL
    payload = {"url": "https://example.com"}
    create_resp = await app.post("/api/v1/shorten", json=payload)
    short_id = create_resp.json()["short_id"]

    # Perform a redirect to increment counter (background task)
    await app.get(f"/api/v1/{short_id}", follow_redirects=False)

    # Wait for background task to complete and counter updated
    click_count = 0
    for _ in range(10):
        stats_resp = await app.get(f"/api/v1/stats/{short_id}")
        if stats_resp.status_code == 200:
            click_count = stats_resp.json()["click_count"]
            if click_count == 1:
                break
        await asyncio.sleep(0.1)
    assert click_count == 1
```

```python
# tests/test_delete.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_soft_delete(app: AsyncClient):
    # Create
    payload = {"url": "https://example.com"}
    create_resp = await app.post("/api/v1/shorten", json=payload)
    short_id = create_resp.json()["short_id"]

    # Delete
    del_resp = await app.delete(f"/api/v1/{short_id}")
    assert del_resp.status_code == 204

    # Redirect should now be 404
    redirect_resp = await app.get(f"/api/v1/{short_id}", follow_redirects=False)
    assert redirect_resp.status_code == 404
```

```python
# tests/test_rate_limit.py
"""
Test rate limiting middleware.
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_rate_limit_headers(app: AsyncClient):
    # Use a valid endpoint that is not excluded
    payload = {"url": "https://example.com"}
    resp = await app.post("/api/v1/shorten", json=payload)
    assert "X-RateLimit-Limit" in resp.headers
    assert "X-RateLimit-Remaining" in resp.headers
```

## Список исправлений по QA Gate:

- 🔴 #1: `app/core/rate_limiter.py` – реализован sliding window с Redis sorted sets вместо fixed‑window.
- 🔴 #2: `app/api/v1/redirect.py` и `app/tasks.py` – заменены FastAPI BackgroundTasks на asyncio.create_task с отслеживанием и ожиданием в lifespan.
- 🔴 #3: `tests/test_stats.py` – добавлен тест `test_stats_after_redirect` с повторными попытками для устранения гонки.
- 🔴 #4: `tests/test_redirect.py` – добавлен тест `test_redirect_expired` на HTTP 410 для истекших ссылок.
- 🟡 #5: Все эндпоинты с `short_id` (`redirect`, `stats`, `delete`) – добавлена валидация через `Path(..., min_length=1, max_length=7, regex=r'^[a-zA-Z0-9]+$')`.
- 🟡 #7: `app/middleware/rate_limit.py` – обработан случай `request.client is None` с fallback на "unknown".
- 🟡 #8: `tests/test_rate_limit.py` – тест исправлен на использование валидного эндпоинта `POST /api/v1/shorten`.
- 🟡 #10: `app/main.py` – Redis инициализация обёрнута в try/except с предупреждением, чтобы приложение не падало при отсутствии Redis.

Проблема #6 (доступ к БД в middleware) оставлена без изменений – архитектурой не предусмотрено связывание rate‑limit с состоянием БД. Проблема #9 уже была корректно реализована (partial index в миграции).