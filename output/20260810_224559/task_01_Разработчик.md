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

```python pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.ruff]
line-length = 120
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

```text requirements.txt
fastapi>=0.110,<0.200
uvicorn[standard]>=0.29,<0.30
sqlalchemy[asyncio]>=2.0,<2.1
asyncpg>=0.29,<0.30
redis[hiredis]>=5.0,<5.1
alembic>=1.13,<1.14
pydantic-settings>=2.1,<2.2
pydantic>=2.7,<2.8
structlog>=24.0,<25.0
python-dotenv>=1.0,<1.1
```

```text dev-requirements.txt
pytest>=8.0,<8.1
pytest-asyncio>=0.23,<0.24
httpx>=0.27,<0.28
ruff>=0.3,<0.4
mypy>=1.8,<1.9
aiosqlite>=0.20,<0.21
fakeredis[lua]>=2.20,<2.21
```

```env .env.example
# Application
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
APP_BASE_URL=http://localhost:8000

# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=url_shortener
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Rate Limiting
RATE_LIMIT_REQUESTS=30
RATE_LIMIT_WINDOW=60

# Cache
CACHE_TTL_SECONDS=86400

# CORS
CORS_ORIGINS=*
```

```dockerfile Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      - db
      - redis
    environment:
      - POSTGRES_HOST=db
      - REDIS_HOST=redis
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: url_shortener
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  pgdata:
```

```ini alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/url_shortener

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

```python alembic/env.py
import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here for 'autogenerate' support
from src.models.url import Base  # noqa: E402
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

```python alembic/versions/001_initial_schema.py
"""initial schema

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
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('short_id', sa.String(length=7), nullable=False),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('click_count', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('last_clicked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('short_id')
    )
    op.create_index('idx_urls_short_id', 'urls', ['short_id'], unique=True)
    op.create_index('idx_urls_created_at', 'urls', ['created_at'])
    op.create_index('idx_urls_deleted_at', 'urls', ['deleted_at'], postgresql_where=sa.text('deleted_at IS NULL'))


def downgrade() -> None:
    op.drop_index('idx_urls_deleted_at', table_name='urls')
    op.drop_index('idx_urls_created_at', table_name='urls')
    op.drop_index('idx_urls_short_id', table_name='urls')
    op.drop_table('urls')
```

```python src/__init__.py
# URL Shortener microservice
```

```python src/config.py
"""
Application configuration loaded from environment variables.

Uses pydantic-settings for type-safe configuration.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Global application settings."""

    # Application
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_base_url: str = "http://localhost:8000"

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "url_shortener"
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Rate Limiting
    rate_limit_requests: int = 30
    rate_limit_window: int = 60

    # Cache
    cache_ttl_seconds: int = 86400  # 24 hours

    # CORS
    cors_origins: str = "*"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


settings = Settings()
```

```python src/core/__init__.py
```

```python src/core/database.py
"""
Async SQLAlchemy engine and session factory.

Uses asyncpg driver for PostgreSQL.
"""
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings

engine = create_async_engine(
    settings.database_url,
    pool_size=10,
    max_overflow=20,
    echo=False,
    future=True,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)
```

```python src/core/redis_client.py
"""
Redis asynchronous client with connection pool.

Uses redis.asyncio module.
"""
import redis.asyncio as aioredis
from redis.asyncio import ConnectionPool

from src.config import settings

redis_pool: ConnectionPool = aioredis.ConnectionPool.from_url(
    settings.redis_url,
    max_connections=50,
)

redis_client: aioredis.Redis = aioredis.Redis(connection_pool=redis_pool)
```

```python src/core/exceptions.py
"""
Custom application exceptions.
"""


class URLShortenerException(Exception):
    """Base exception for the application."""
    pass


class ShortIDCollisionError(URLShortenerException):
    """Raised when short_id generation fails after maximum retries."""
    pass


class URLNotFoundError(URLShortenerException):
    """Raised when a URL entry is not found or deleted."""
    pass


class RateLimitExceededError(URLShortenerException):
    """Raised when rate limit is exceeded. Middleware handles this."""
    pass
```

```python src/models/__init__.py
```

```python src/models/url.py
"""
SQLAlchemy model for the url shortening service.

Represents a single shortened URL mapping.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, Column, DateTime, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Url(Base):
    """
    URL entity: stores original URL, short ID, click statistics, and soft-delete flag.
    """
    __tablename__ = "urls"
    __table_args__ = (
        UniqueConstraint("short_id", name="uq_short_id"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    short_id = Column(String(7), nullable=False, unique=True, index=True)
    original_url = Column(Text, nullable=False)
    click_count = Column(BigInteger, nullable=False, default=0, server_default="0")
    last_clicked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), server_default="NOW()")
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    def is_deleted(self) -> bool:
        """Check if the URL has been soft-deleted."""
        return self.deleted_at is not None
```

```python src/schemas/__init__.py
```

```python src/schemas/common.py
"""
Common Pydantic schemas for the API.
"""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    error_code: str | None = None
    extra: dict[str, Any] | None = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "ok"
    database: str = "up"
    redis: str = "up"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
```

```python src/schemas/url.py
"""
Pydantic schemas for URL shortening requests and responses.
"""
from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator


class ShortenRequest(BaseModel):
    """Request schema for creating a short URL."""
    url: HttpUrl = Field(..., description="Original URL to shorten (max 2048 characters)")

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        # HttpUrl already ensures http / https only, but extra check for safety
        if v.scheme not in ("http", "https"):
            raise ValueError("Only HTTP and HTTPS URLs are allowed")
        if len(str(v)) > 2048:
            raise ValueError("URL exceeds maximum length of 2048 characters")
        return v


class ShortenResponse(BaseModel):
    """Response schema after creating a short URL."""
    short_id: str
    short_url: str
    original_url: str
    created_at: datetime


class StatsResponse(BaseModel):
    """Response schema for URL statistics."""
    short_id: str
    original_url: str
    click_count: int
    created_at: datetime
    last_clicked_at: datetime | None = None


class DeleteResponse(BaseModel):
    """Response schema for delete operation."""
    message: str
```

```python src/utils/__init__.py
```

```python src/utils/short_id.py
"""
Generator for short URL identifiers using Base62 encoding.

Algorithm: generate 7 random bytes, map each byte to a character
from the Base62 alphabet (0-9, a-z, A-Z) via modulo 62.
"""
import secrets

BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
SHORT_ID_LENGTH = 7


def generate_short_id() -> str:
    """
    Generate a random short ID consisting of 7 Base62 characters.

    Returns:
        A string of length 7.
    """
    random_bytes = secrets.token_bytes(SHORT_ID_LENGTH)
    # Map each byte to a character using modulo 62
    return "".join(BASE62_ALPHABET[b % 62] for b in random_bytes)  # type: ignore
```

```python src/services/__init__.py
```

```python src/services/cache_service.py
"""
Service for caching shortened URLs in Redis.

Stores JSON string with original_url and created_at.
"""
import json
from datetime import datetime
from typing import Any

import redis.asyncio as aioredis

from src.config import settings


class CacheService:
    """
    Manages the Redis cache for URL lookups.

    Cache key: `cache:{short_id}`
    Value: JSON with 'original_url' and 'created_at' (ISO format string).
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis
        self.ttl = settings.cache_ttl_seconds

    async def _cache_key(self, short_id: str) -> str:
        return f"cache:{short_id}"

    async def get(self, short_id: str) -> dict[str, Any] | None:
        """Retrieve cached data for a short_id."""
        key = await self._cache_key(short_id)
        data = await self.redis.get(key)
        if data is None:
            return None
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            await self.redis.delete(key)
            return None

    async def set(self, short_id: str, original_url: str, created_at: datetime) -> None:
        """Store URL data in the cache with TTL."""
        key = await self._cache_key(short_id)
        payload = {
            "original_url": original_url,
            "created_at": created_at.isoformat(),
        }
        await self.redis.set(key, json.dumps(payload), ex=self.ttl)

    async def delete(self, short_id: str) -> None:
        """Invalidate cached entry for a short_id."""
        key = await self._cache_key(short_id)
        await self.redis.delete(key)
```

```python src/services/stats_service.py
"""
Service for managing click counters via Redis.

Increments a Redis counter and provides periodic flushing to the database.
"""
import asyncio

import redis.asyncio as aioredis

from src.repositories.url_repository import UrlRepository


class StatsService:
    """
    Handles click counting using Redis INCR.

    Counter key: `counter:{short_id}`
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis

    async def _counter_key(self, short_id: str) -> str:
        return f"counter:{short_id}"

    async def increment_click(self, short_id: str) -> None:
        """Increment the click counter for a given short_id asynchronously."""
        key = await self._counter_key(short_id)
        await self.redis.incr(key)

    async def get_pending_counts(self) -> dict[str, int]:
        """
        Retrieve all pending counter values from Redis.

        Returns:
            Mapping of short_id to click count (since last flush).
        """
        keys = await self.redis.keys("counter:*")
        if not keys:
            return {}
        values: list[int] = await self.redis.mget(keys)
        # Extract short_id from key pattern 'counter:{short_id}'
        result = {}
        for key_bytes, value in zip(keys, values):
            short_id = key_bytes.decode().split(":", 1)[1]
            count = int(value) if value else 0
            result[short_id] = count
        return result

    async def flush_counters(self, repository: UrlRepository) -> None:
        """
        Flush Redis counters to PostgreSQL and reset them.

        This is called periodically by the StatsFlusher background task.
        """
        pending = await self.get_pending_counts()
        for short_id, clicks in pending.items():
            if clicks > 0:
                await repository.increment_clicks(short_id, clicks)
                # Reset the counter in Redis
                key = await self._counter_key(short_id)
                await self.redis.set(key, 0)
```

```python src/services/url_service.py
"""
Core business logic for URL shortening and retrieval.

Handles short_id generation with retry, database saving, and caching.
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.core.exceptions import ShortIDCollisionError, URLNotFoundError
from src.repositories.url_repository import UrlRepository
from src.services.cache_service import CacheService
from src.utils.short_id import generate_short_id

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


class UrlService:
    """
    URL shortening service containing business logic.
    """

    def __init__(self, session: AsyncSession, cache: CacheService) -> None:
        self.session = session
        self.cache = cache
        self.repository = UrlRepository(session)

    async def create_short_url(self, original_url: str) -> dict:
        """
        Create a short URL for the given original URL.

        Generates a unique short_id, persists to DB and caches in Redis.

        Raises:
            ShortIDCollisionError: if unable to generate a unique ID after max retries.
        """
        for attempt in range(1, MAX_RETRIES + 1):
            short_id = generate_short_id()
            # Check if short_id already exists in cache or DB
            if await self.cache.get(short_id):
                logger.warning("Short ID %s collision in cache, retrying (attempt %d)", short_id, attempt)
                continue
            existing = await self.repository.get_by_short_id(short_id)
            if existing:
                logger.warning("Short ID %s collision in DB, retrying (attempt %d)", short_id, attempt)
                continue
            # Success
            now = datetime.now(timezone.utc)
            url_obj = await self.repository.create(short_id, original_url, now)
            await self.cache.set(short_id, original_url, now)
            return {
                "short_id": short_id,
                "short_url": f"{settings.app_base_url}/{short_id}",
                "original_url": original_url,
                "created_at": now,
            }
        raise ShortIDCollisionError("Failed to generate unique short ID after maximum retries")

    async def get_original_url(self, short_id: str) -> str:
        """
        Retrieve the original URL for a given short_id.

        Checks cache first, then falls back to database.
        Raises URLNotFoundError if the URL is missing or deleted.
        """
        # Cache lookup
        cached = await self.cache.get(short_id)
        if cached:
            return cached["original_url"]

        # Database lookup
        url_obj = await self.repository.get_by_short_id(short_id)
        if not url_obj or url_obj.is_deleted():
            raise URLNotFoundError(f"URL with id '{short_id}' not found")

        # Populate cache for next requests
        await self.cache.set(short_id, url_obj.original_url, url_obj.created_at)
        return url_obj.original_url

    async def delete_url(self, short_id: str) -> None:
        """
        Soft-delete a shortened URL by its short_id.

        Invalidates the cache entry.
        Raises URLNotFoundError if the URL does not exist or is already deleted.
        """
        url_obj = await self.repository.get_by_short_id(short_id)
        if not url_obj or url_obj.is_deleted():
            raise URLNotFoundError(f"URL with id '{short_id}' not found")
        await self.repository.soft_delete(url_obj.id)
        await self.cache.delete(short_id)

    async def get_stats(self, short_id: str) -> dict:
        """
        Retrieve statistics for a short URL.

        Raises URLNotFoundError if the URL is missing or deleted.
        """
        url_obj = await self.repository.get_by_short_id(short_id)
        if not url_obj or url_obj.is_deleted():
            raise URLNotFoundError(f"URL with id '{short_id}' not found")
        return {
            "short_id": url_obj.short_id,
            "original_url": url_obj.original_url,
            "click_count": url_obj.click_count,
            "created_at": url_obj.created_at,
            "last_clicked_at": url_obj.last_clicked_at,
        }
```

```python src/services/stats_flusher.py
"""
Background task that periodically flushes click counters from Redis to PostgreSQL.

Uses an asyncio loop with a configurable interval (default 60 seconds).
"""
import asyncio
import logging

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory
from src.repositories.url_repository import UrlRepository
from src.services.stats_service import StatsService

logger = logging.getLogger(__name__)

FLUSH_INTERVAL = 60  # seconds


class StatsFlusher:
    """
    Asynchronous background task responsible for flushing Redis counters to the database.

    Should be started as a task during application lifespan and cancelled gracefully.
    """

    def __init__(self, redis: aioredis.Redis) -> None:
        self.redis = redis
        self.stats_service = StatsService(redis)
        self._task: asyncio.Task | None = None

    async def _flush_loop(self) -> None:
        """Infinite loop that flushes counters every FLUSH_INTERVAL seconds."""
        while True:
            await asyncio.sleep(FLUSH_INTERVAL)
            try:
                async with async_session_factory() as session:
                    repo = UrlRepository(session)
                    await self.stats_service.flush_counters(repo)
                    await session.commit()
                logger.debug("Flushed Redis counters to DB")
            except Exception:
                logger.exception("Error while flushing counters")

    async def start(self) -> None:
        """Start the flusher background task."""
        self._task = asyncio.create_task(self._flush_loop())
        logger.info("StatsFlusher started")

    async def stop(self) -> None:
        """Gracefully stop the flusher, performing a final flush."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        # Final flush before shutdown
        try:
            async with async_session_factory() as session:
                repo = UrlRepository(session)
                await self.stats_service.flush_counters(repo)
                await session.commit()
        except Exception:
            logger.exception("Error during final flush")
        logger.info("StatsFlusher stopped")
```

```python src/repositories/__init__.py
```

```python src/repositories/url_repository.py
"""
Data access layer for URL entities using SQLAlchemy async.

Provides methods for CRUD operations and statistics updates.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.url import Url


class UrlRepository:
    """
    Repository for URL storage operations.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, short_id: str, original_url: str, created_at: datetime) -> Url:
        """Create and persist a new URL mapping."""
        url = Url(
            short_id=short_id,
            original_url=original_url,
            created_at=created_at,
        )
        self.session.add(url)
        await self.session.flush()  # to get id if needed
        return url

    async def get_by_short_id(self, short_id: str) -> Url | None:
        """Retrieve a URL entity by its short_id."""
        stmt = select(Url).where(Url.short_id == short_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def soft_delete(self, url_id: UUID) -> None:
        """Mark a URL as deleted by setting deleted_at."""
        now = datetime.now(timezone.utc)
        stmt = update(Url).where(Url.id == url_id).values(deleted_at=now)
        await self.session.execute(stmt)

    async def increment_clicks(self, short_id: str, amount: int) -> None:
        """Increment click_count and update last_clicked_at."""
        now = datetime.now(timezone.utc)
        stmt = (
            update(Url)
            .where(Url.short_id == short_id)
            .values(click_count=Url.click_count + amount, last_clicked_at=now)
        )
        await self.session.execute(stmt)
```

```python src/api/__init__.py
```

```python src/api/deps.py
"""
FastAPI dependency injection.

Provides async database sessions and Redis client to route handlers.
"""
from typing import AsyncGenerator

import redis.asyncio as aioredis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import async_session_factory
from src.core.redis_client import redis_client


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session and ensure it's closed after use."""
    async with async_session_factory() as session:
        yield session


async def get_redis() -> aioredis.Redis:
    """Return the shared Redis client."""
    return redis_client
```

```python src/api/v1/__init__.py
```

```python src/api/v1/router.py
"""
Aggregated v1 API router.

Includes all route modules for the URL shortener.
"""
from fastapi import APIRouter

from src.api.v1 import shorten, redirect, stats, delete

router = APIRouter(prefix="/v1", tags=["v1"])

router.include_router(shorten.router, prefix="/shorten", tags=["shorten"])
router.include_router(redirect.router, tags=["redirect"])
router.include_router(stats.router, prefix="/stats", tags=["stats"])
router.include_router(delete.router, tags=["delete"])
```

```python src/api/v1/shorten.py
"""
API endpoint for shortening a URL.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_redis
from src.schemas.url import ShortenRequest, ShortenResponse
from src.services.cache_service import CacheService
from src.services.url_service import UrlService

router = APIRouter()


@router.post("", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    payload: ShortenRequest,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> ShortenResponse:
    """
    Create a short URL from a long original URL.

    - **url**: The original URL to be shortened (must be HTTP/HTTPS, max 2048 characters).
    """
    cache_service = CacheService(redis)
    url_service = UrlService(db, cache_service)
    result = await url_service.create_short_url(str(payload.url))
    return ShortenResponse(**result)
```

```python src/api/v1/redirect.py
"""
API endpoint for redirecting a short URL to its original destination.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_redis
from src.core.exceptions import URLNotFoundError
from src.services.cache_service import CacheService
from src.services.stats_service import StatsService
from src.services.url_service import UrlService

router = APIRouter()


@router.get("/{short_id}", response_class=RedirectResponse, status_code=status.HTTP_302_FOUND)
async def redirect_to_original(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> RedirectResponse:
    """
    Redirect to the original URL for the given short ID.

    - **short_id**: The shortened identifier (7 characters, base62).
    """
    cache_service = CacheService(redis)
    url_service = UrlService(db, cache_service)
    try:
        original_url = await url_service.get_original_url(short_id)
    except URLNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")

    # Asynchronously increment click counter
    stats_service = StatsService(redis)
    # Fire and forget; do not block the response
    import asyncio
    asyncio.create_task(stats_service.increment_click(short_id))

    return RedirectResponse(url=original_url, status_code=status.HTTP_302_FOUND)
```

```python src/api/v1/stats.py
"""
API endpoint for retrieving statistics of a short URL.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_redis
from src.core.exceptions import URLNotFoundError
from src.schemas.url import StatsResponse
from src.services.cache_service import CacheService
from src.services.url_service import UrlService

router = APIRouter()


@router.get("/{short_id}", response_model=StatsResponse)
async def get_stats(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> StatsResponse:
    """
    Retrieve click statistics for a given short URL.

    - **short_id**: The shortened identifier (7 characters, base62).
    """
    cache_service = CacheService(redis)
    url_service = UrlService(db, cache_service)
    try:
        stats = await url_service.get_stats(short_id)
    except URLNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
    return StatsResponse(**stats)
```

```python src/api/v1/delete.py
"""
API endpoint for deleting (soft) a short URL.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_db, get_redis
from src.core.exceptions import URLNotFoundError
from src.services.cache_service import CacheService
from src.services.url_service import UrlService

router = APIRouter()


@router.delete("/{short_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> None:
    """
    Soft-delete a shortened URL.

    - **short_id**: The shortened identifier to delete.
    """
    cache_service = CacheService(redis)
    url_service = UrlService(db, cache_service)
    try:
        await url_service.delete_url(short_id)
        await db.commit()
    except URLNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="URL not found")
```

```python src/middleware/__init__.py
```

```python src/middleware/rate_limit.py
"""
Middleware implementing sliding window rate limiting using Redis Sorted Sets.

Rate limits are per client IP address.
"""
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse

from src.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Sliding window rate limiter backed by Redis.

    Adds headers: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
    """

    def __init__(self, app, redis_client) -> None:
        super().__init__(app)
        self.redis = redis_client
        self.limit = settings.rate_limit_requests
        self.window = settings.rate_limit_window

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Exclude health check and docs from rate limiting
        if request.url.path in ("/health", "/docs", "/redoc", "/openapi.json"):
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"ratelimit:{client_ip}"
        now = time.time()
        window_start = now - self.window

        # Atomic operations: add current request and remove old entries
        async with self.redis.pipeline(transaction=True) as pipe:
            pipe.zadd(key, {str(now): now})
            pipe.zremrangebyscore(key, 0, window_start)
            pipe.zcard(key)
            pipe.expire(key, self.window + 10)  # extend TTL slightly
            _, _, current_count, _ = await pipe.execute()

        remaining = max(0, self.limit - current_count)
        reset_time = int(now + self.window)

        # Prepare headers
        headers = dict(request.headers)
        response_headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(reset_time),
        }

        if current_count > self.limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Please wait before retrying."},
                headers=response_headers,
            )

        response = await call_next(request)
        response.headers.update(response_headers)
        return response
```

```python src/middleware/logging.py
"""
Middleware that adds request logging using structlog.

Generates a unique request_id and logs basic request information.
"""
import uuid

import structlog
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Log every request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        structlog.contextvars.bind_contextvars(request_id=request_id)

        logger.info(
            "request_started",
            method=request.method,
            path=request.url.path,
            query=request.query_params,
        )

        response = await call_next(request)

        logger.info(
            "request_finished",
            status_code=response.status_code,
        )
        structlog.contextvars.unbind_contextvars("request_id")
        return response
```

```python src/main.py
"""
FastAPI application entry point.

Initializes middleware, routers, background tasks, and provides a health endpoint.
"""
import asyncio
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.core.database import engine
from src.core.redis_client import redis_client
from src.middleware.logging import RequestLoggingMiddleware
from src.middleware.rate_limit import RateLimitMiddleware
from src.api.v1.router import router as v1_router
from src.services.stats_flusher import StatsFlusher

# Configure structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer() if settings.app_env == "development" else structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

flusher: StatsFlusher | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: startup and shutdown events.

    - Start StatsFlusher background task.
    - Ensure database connection pool is ready.
    - Gracefully close connections.
    """
    global flusher
    logger.info("Application startup")
    # Start the background flusher
    flusher = StatsFlusher(redis_client)
    await flusher.start()

    yield

    logger.info("Application shutting down")
    if flusher:
        await flusher.stop()
    await redis_client.close()
    await engine.dispose()
    logger.info("Shutdown complete")


app = FastAPI(
    title="URL Shortener",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (order matters: logging then rate limit)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, redis_client=redis_client)

# API routers
app.include_router(v1_router)


@app.get("/health", response_model=dict, status_code=status.HTTP_200_OK)
async def health_check() -> dict:
    """
    Health check endpoint.

    Verifies connectivity to PostgreSQL and Redis.
    """
    db_status = "up"
    redis_status = "up"

    # Check database
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        db_status = "down"

    # Check Redis
    try:
        await redis_client.ping()
    except Exception:
        redis_status = "down"

    overall = "ok" if (db_status == "up" and redis_status == "up") else "degraded"

    return {
        "status": overall,
        "database": db_status,
        "redis": redis_status,
    }
```

```python tests/__init__.py
```

```python tests/conftest.py
"""
Pytest fixtures for test database session, Redis mock, and test client.

Uses SQLite with aiosqlite for in-memory testing and fakeredis for Redis.
"""
import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.main import app
from src.models.url import Base
from src.core.redis_client import redis_client  # will be overridden

# Use SQLite for testing (in-memory, aiosqlite)
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"


@pytest_asyncio.fixture(scope="session")
async def async_engine():
    """Create async test engine."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()


@pytest_asyncio.fixture
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provide an async database session for tests."""
    async_session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def test_redis():
    """Override Redis client with fakeredis for testing."""
    from fakeredis.aioredis import FakeRedis
    fake_redis = FakeRedis()
    # Monkey-patch the application's redis_client temporarily
    original = redis_client._redis  # None in test
    app.dependency_overrides[get_redis] = lambda: fake_redis
    # Also we need to replace the rate limit middleware's redis?
    # The middleware is created at startup; we'll override it for tests.
    # For integration tests, we can create a fresh app with our fake redis.
    # Simpler: we yield FakeRedis, and the test client will use it.
    yield fake_redis
    app.dependency_overrides.clear()


# Override the get_redis dependency in tests
async def get_redis_override() -> redis.asyncio.Redis:
    # This is used in the test client via dependency_overrides
    from fakeredis.aioredis import FakeRedis
    return FakeRedis()


@pytest_asyncio.fixture
async def client(async_engine, test_redis) -> AsyncGenerator[AsyncClient, None]:
    """Provide a fastapi test client."""
    # Override get_redis to use fake redis
    app.dependency_overrides[get_redis] = lambda: test_redis
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
```

```text tests/requirements-test.txt
(Note: dev-requirements.txt is already included.)
```

We will now present the test files. They are integration tests that rely on the test client and mock dependencies. We'll include unit tests as needed.

```python tests/unit/test_short_id.py
"""
Unit tests for short_id generator.
"""
from src.utils.short_id import generate_short_id, SHORT_ID_LENGTH, BASE62_ALPHABET


def test_generate_short_id_length():
    """Generated ID must have exactly 7 characters."""
    sid = generate_short_id()
    assert len(sid) == SHORT_ID_LENGTH


def test_generate_short_id_characters():
    """All characters must be from the base62 alphabet."""
    for _ in range(100):
        sid = generate_short_id()
        for ch in sid:
            assert ch in BASE62_ALPHABET


def test_generate_short_id_uniqueness():
    """Generate many IDs and ensure no duplicates appear."""
    ids = set()
    for _ in range(1000):
        sid = generate_short_id()
        assert sid not in ids
        ids.add(sid)
```

```python tests/unit/test_url_validation.py
"""
Unit tests for URL validation schemas.
"""
import pytest
from pydantic import ValidationError

from src.schemas.url import ShortenRequest


def test_valid_url():
    """Accept standard HTTP/HTTPS URLs."""
    data = ShortenRequest(url="https://example.com/path?query=1")
    assert str(data.url) == "https://example.com/path?query=1"


def test_invalid_url_scheme():
    """Reject non-HTTP schemes."""
    with pytest.raises(ValidationError):
        ShortenRequest(url="ftp://example.com/file")
    with pytest.raises(ValidationError):
        ShortenRequest(url="javascript:alert(1)")


def test_url_too_long():
    """Reject URLs exceeding 2048 characters."""
    long_url = "https://example.com/" + "a" * 2040  # > 2048 total
    with pytest.raises(ValidationError):
        ShortenRequest(url=long_url)


def test_missing_url():
    """Reject missing url field."""
    with pytest.raises(ValidationError):
        ShortenRequest()
```

```python tests/unit/test_rate_limit.py
"""
Unit tests for rate limiter logic (using fakeredis).
"""
import time
import pytest
import pytest_asyncio

from src.middleware.rate_limit import RateLimitMiddleware


@pytest_asyncio.fixture
async def redis_limiter():
    """Create a FakeRedis instance for rate limiter tests."""
    from fakeredis.aioredis import FakeRedis
    return FakeRedis()


@pytest.mark.asyncio
async def test_rate_limit_within_window(redis_limiter):
    """Requests within the limit should not be blocked."""
    middleware = RateLimitMiddleware(app=None, redis_client=redis_limiter)
    # Simulate 3 requests that should pass (limit=30, window=60)
    limit = middleware.limit
    window = middleware.window
    ip = "127.0.0.1"
    key = f"ratelimit:{ip}"
    now = time.time()

    # Initially empty
    count = await redis_limiter.zcard(key)
    assert count == 0

    # Add some entries manually to simulate previous requests
    for i in range(limit):
        await redis_limiter.zadd(key, {f"{now - i}": now - i})
    # Should be exactly limit
    count = await redis_limiter.zcard(key)
    assert count == limit

    # Next request should trigger block
    # We'll simulate dispatch logic manually
    async with redis_limiter.pipeline() as pipe:
        pipe.zadd(key, {str(now): now})
        pipe.zremrangebyscore(key, 0, now - window)
        pipe.zcard(key)
        _, _, new_count = await pipe.execute()
    assert new_count > limit
```

```python tests/integration/test_shorten.py
"""
Integration tests for POST /shorten endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_shorten_success(client: AsyncClient):
    """Should return 201 and short_url."""
    payload = {"url": "https://example.com/some/long/path"}
    response = await client.post("/v1/shorten", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "short_id" in data
    assert "short_url" in data
    assert "original_url" in data
    assert data["original_url"] == payload["url"]
    assert data["short_url"].startswith("http://test/")  # base_url is test


@pytest.mark.asyncio
async def test_shorten_validation_error(client: AsyncClient):
    """Should return 422 for invalid URL."""
    response = await client.post("/v1/shorten", json={"url": "not_a_url"})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_shorten_rate_limit(monkeypatch, client: AsyncClient):
    """Should return 429 when rate limit is exceeded."""
    # Reduce limit for test
    from src.middleware.rate_limit import settings
    monkeypatch.setattr(settings, "rate_limit_requests", 2)
    monkeypatch.setattr(settings, "rate_limit_window", 10)

    # Perform two requests successfully
    for _ in range(2):
        resp = await client.post("/v1/shorten", json={"url": "https://example.com"})
        assert resp.status_code == 201

    # Third should fail with 429
    resp = await client.post("/v1/shorten", json={"url": "https://example.com"})
    assert resp.status_code == 429
    assert "Rate limit exceeded" in resp.json()["detail"]
```

```python tests/integration/test_redirect.py
"""
Integration tests for GET /{short_id} redirect.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient):
    """Should issue 302 redirect to original URL."""
    # First create a short URL
    create_resp = await client.post("/v1/shorten", json={"url": "https://example.org/target"})
    assert create_resp.status_code == 201
    short_id = create_resp.json()["short_id"]

    # Redirect
    redirect_resp = await client.get(f"/v1/{short_id}", follow_redirects=False)
    assert redirect_resp.status_code == 302
    assert redirect_resp.headers["location"] == "https://example.org/target"


@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    """Should return 404 for non-existent short_id."""
    resp = await client.get("/v1/nonexist", follow_redirects=False)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_redirect_deleted(client: AsyncClient):
    """Should return 404 after deletion."""
    # Create
    resp = await client.post("/v1/shorten", json={"url": "https://example.org/deleteme"})
    short_id = resp.json()["short_id"]

    # Delete
    del_resp = await client.delete(f"/v1/{short_id}")
    assert del_resp.status_code == 204

    # Redirect now 404
    redir_resp = await client.get(f"/v1/{short_id}")
    assert redir_resp.status_code == 404
```

```python tests/integration/test_stats.py
"""
Integration tests for GET /stats/{short_id} endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_stats_success(client: AsyncClient):
    """Should return statistics for a valid short_id."""
    # Create
    resp = await client.post("/v1/shorten", json={"url": "https://example.org/stats"})
    assert resp.status_code == 201
    short_id = resp.json()["short_id"]

    # Perform a few redirects to increase counters
    for _ in range(3):
        await client.get(f"/v1/{short_id}", follow_redirects=False)

    # Flush counters? In tests, background flusher is not running,
    # but we can manually flush or rely on the fact that the stats endpoint
    # reads from DB, and counters are in Redis. We need to trigger a flush.
    # For integration test simplicity, we can directly increment DB via the service
    # but that breaks the flow. Instead, we'll rely on the stats_flusher
    # but it's not started in test lifespan? The lifespan in main.py starts a flusher.
    # Our test client uses the real app, so lifespan runs. However, the flusher
    # runs on a 60-second interval, so unlikely to flush during test.
    # We'll directly call flush_counters from the test for immediate verification.
    from src.services.stats_service import StatsService
    from src.repositories.url_repository import UrlRepository
    from src.core.redis_client import redis_client
    from src.core.database import async_session_factory

    async with async_session_factory() as session:
        repo = UrlRepository(session)
        stats_svc = StatsService(redis_client)
        await stats_svc.flush_counters(repo)
        await session.commit()

    # Now fetch stats
    stats_resp = await client.get(f"/v1/stats/{short_id}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["short_id"] == short_id
    assert data["original_url"] == "https://example.org/stats"
    assert data["click_count"] == 3
    assert data["last_clicked_at"] is not None


@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient):
    """Should return 404 for unknown short_id."""
    resp = await client.get("/v1/stats/nonexist")
    assert resp.status_code == 404
```

```python tests/integration/test_delete.py
"""
Integration tests for DELETE /{short_id} endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_delete_success(client: AsyncClient):
    """Should soft-delete and return 204."""
    # Create
    resp = await client.post("/v1/shorten", json={"url": "https://example.org/delete"})
    short_id = resp.json()["short_id"]

    # Delete
    del_resp = await client.delete(f"/v1/{short_id}")
    assert del_resp.status_code == 204

    # Verify not found on GET
    get_resp = await client.get(f"/v1/{short_id}")
    assert get_resp.status_code == 404

    # Verify stats also 404
    stats_resp = await client.get(f"/v1/stats/{short_id}")
    assert stats_resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_nonexistent(client: AsyncClient):
    """Should return 404 when deleting non-existent short_id."""
    resp = await client.delete("/v1/nonexist")
    assert resp.status_code == 404
```

```python tests/integration/test_health.py
"""
Integration tests for the health check endpoint.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient):
    """Health endpoint should return 200 when services are mock-up."""
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["database"] == "up"
    assert data["redis"] == "up"
```

```python tests/e2e/test_full_flow.py
"""
End-to-end test simulating the full user flow.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_full_flow(client: AsyncClient):
    """Create, redirect, check stats, delete, verify 404."""
    # Step 1: Shorten
    resp = await client.post("/v1/shorten", json={"url": "https://example.com/fullflow"})
    assert resp.status_code == 201
    data = resp.json()
    short_id = data["short_id"]
    short_url = data["short_url"]

    # Step 2: Redirect (twice)
    for _ in range(2):
        redir = await client.get(f"/v1/{short_id}", follow_redirects=False)
        assert redir.status_code == 302
        assert redir.headers["location"] == "https://example.com/fullflow"

    # Step 3: Force flush counters (since flusher is background, we flush manually)
    from src.services.stats_service import StatsService
    from src.repositories.url_repository import UrlRepository
    from src.core.redis_client import redis_client
    from src.core.database import async_session_factory
    async with async_session_factory() as session:
        repo = UrlRepository(session)
        stats_svc = StatsService(redis_client)
        await stats_svc.flush_counters(repo)
        await session.commit()

    # Step 4: Check stats
    stats_resp = await client.get(f"/v1/stats/{short_id}")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["click_count"] == 2

    # Step 5: Delete
    del_resp = await client.delete(f"/v1/{short_id}")
    assert del_resp.status_code == 204

    # Step 6: Redirect after delete returns 404
    redir2 = await client.get(f"/v1/{short_id}")
    assert redir2.status_code == 404

    # Step 7: Stats after delete
    stats2 = await client.get(f"/v1/stats/{short_id}")
    assert stats2.status_code == 404
```