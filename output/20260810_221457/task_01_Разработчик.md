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

```toml pyproject.toml
[project]
name = "url-shortener"
version = "0.1.0"
description = "URL Shortener microservice"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",
    "redis[hiredis]>=5.0.1",
    "pydantic-settings>=2.1.0",
    "alembic>=1.13.1",
    "python-dotenv>=1.0.1"
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.3",
    "httpx>=0.26.0",
    "fakeredis[lua]>=2.20.0",  # for async Redis testing
    "aiosqlite>=0.19.0"        # for async SQLite testing
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

```bash .env.example
APP_HOST=0.0.0.0
APP_PORT=8000
APP_BASE_URL=https://sho.rt
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/urlshortener
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_PER_MINUTE=100
CACHE_TTL_SECONDS=3600
SHUTDOWN_TIMEOUT_SECONDS=30
LOG_LEVEL=INFO
```

```dockerfile Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY pyproject.toml .
RUN pip install --no-cache-dir -e ".[dev]"  # dev includes test deps, separate stage
# For production, only install main dependencies
RUN pip install --no-cache-dir .

COPY . .

# Run uvicorn
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
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
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d urlshortener"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

```ini alembic.ini
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

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import settings
from src.models import Base  # Import all models so metadata is populated

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    url = settings.DATABASE_URL
    connectable = create_async_engine(url)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

```python alembic/versions/001_initial.py
"""initial

Revision ID: 001
Revises:
Create Date: 2025-03-15

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'url_mapping',
        sa.Column('id', sa.String(7), primary_key=True),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('click_count', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    )
    op.create_index('idx_original_url', 'url_mapping', ['original_url'])
    op.create_index('idx_expires_at', 'url_mapping', ['expires_at'], postgresql_where=sa.text('is_deleted = FALSE'))

def downgrade():
    op.drop_index('idx_expires_at')
    op.drop_index('idx_original_url')
    op.drop_table('url_mapping')
```

```python src/__init__.py
"""
    URL Shortener microservice.

    Strictly follows architecture document: provides API for shortening,
    redirecting, retrieving stats, and deleting URLs.
"""
```

```python src/main.py
"""
    FastAPI application entry point.

    Sets up all middlewares, routers, and startup/shutdown events.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from src.api.router import api_router
from src.config import settings
from src.db.postgres import engine, async_session_maker
from src.db.redis import get_redis
from src.middleware.error_handler import ErrorHandlingMiddleware
from src.middleware.rate_limiter import RateLimiterMiddleware
from src.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect to Redis and create database pool
    # Redis pool is created lazily; we just ensure configuration works
    logger.info("Application starting up")
    async with engine.begin() as conn:
        # Optionally run migrations or just verify connectivity
        pass
    yield
    # Shutdown: dispose DB engine, close Redis pool
    logger.info("Application shutting down")
    await engine.dispose()
    redis = await get_redis()
    await redis.close()

app = FastAPI(
    title="URL Shortener",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Security headers can be added via a dedicated middleware or Starlette's
# We'll rely on a reverse proxy for HSTS etc., but we can add simple ones:
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

# Middleware order (outermost first):
# 1. ErrorHandling – catches exceptions and formats JSON errors
# 2. RateLimiter – blocks if too many requests
# 3. RequestID – attaches UUID to every request
# 4. SecurityHeaders – sets security headers
# FastAPI built-in middlewares (GZip, TrustedHost, etc.) can be added after.
# Note: Built-in middlewares use `app.add_middleware(...)`, which wraps in order.
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
# GZip for compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add routers
app.include_router(api_router)

# Health check (not requiring DB/Redis)
@app.get("/health")
async def health():
    return {"status": "ok"}

# Readiness check – verifies DB connectivity
@app.get("/ready")
async def ready():
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not ready"}, 503
```

```python src/config.py
"""
    Application settings using pydantic-settings.
"""
from pydantic import AnyHttpUrl, validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    BASE_URL: str = "https://sho.rt"  # Used in responses, not the bound address
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener"
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 100
    CACHE_TTL_SECONDS: int = 3600
    SHUTDOWN_TIMEOUT_SECONDS: int = 30
    LOG_LEVEL: str = "INFO"

    # Optional: blocked hosts for SSRF protection (comma-separated)
    BLOCKED_HOSTS: str = "localhost,127.0.0.1,10.,192.168."

    @property
    def blocked_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.BLOCKED_HOSTS.split(",") if h.strip()]

settings = Settings()
```

```python src/db/postgres.py
"""
    PostgreSQL async engine and session factory using SQLAlchemy 2.0.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    """Dependency yielding an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

```python src/db/redis.py
"""
    Redis async client factory and connection pool.
"""
import logging

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

from src.config import settings

logger = logging.getLogger(__name__)

pool: ConnectionPool | None = None

async def create_redis_pool() -> ConnectionPool:
    global pool
    if pool is None:
        pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
        )
        logger.info("Redis connection pool created")
    return pool

async def get_redis() -> aioredis.Redis:
    """Dependency providing Redis client from the pool."""
    p = await create_redis_pool()
    return aioredis.Redis(connection_pool=p)

async def close_redis_pool():
    global pool
    if pool:
        await pool.disconnect()
        pool = None
```

```python src/dependencies.py
"""
    Dependency injection container; re-exports commonly used dependencies.
"""
from src.db.postgres import get_db
from src.db.redis import get_redis

# For simplicity, these are just imported. In larger projects one might
# add more complex dependencies.
```

```python src/models/__init__.py
"""
    SQLAlchemy models package.
"""
from src.models.url_mapping import UrlMapping

__all__ = ["UrlMapping"]

# For Alembic metadata target
Base = UrlMapping.metadata
```

```python src/models/url_mapping.py
"""
    SQLAlchemy ORM model for url_mapping table.
"""
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Boolean, BigInteger, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class UrlMapping(Base):
    __tablename__ = "url_mapping"

    id: Mapped[str] = mapped_column(String(7), primary_key=True)
    original_url: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean(), server_default="false", nullable=False)
    click_count: Mapped[int] = mapped_column(BigInteger(), server_default="0", nullable=False)

    def __repr__(self):
        return f"<UrlMapping(id={self.id}, original_url={self.original_url[:30]}...)>"
```

```python src/schemas/__init__.py
"""
    Pydantic schemas package.
"""
```

```python src/schemas/errors.py
"""
    Standard error response schema.
"""
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str | None = None
```

```python src/schemas/shorten.py
"""
    Schemas for /shorten endpoint.
"""
from datetime import datetime
from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional

class ShortenRequest(BaseModel):
    url: str  # We'll use custom validator because HttpUrl accepts only valid URLs
    expires_at: Optional[datetime] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        # Perform advanced validation via our utility
        from src.utils.url_validator import validate_url
        return validate_url(v)

class ShortenResponse(BaseModel):
    short_id: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
```

```python src/schemas/stats.py
"""
    Schemas for /stats/{id} endpoint.
"""
from datetime import datetime
from pydantic import BaseModel

class StatsResponse(BaseModel):
    short_id: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
```

```python src/utils/__init__.py
"""
    Utility modules.
"""
```

```python src/utils/base62.py
"""
    Base62 encoding/decoding.
    Uses characters A-Z, a-z, 0-9.
"""
import string
import secrets

ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits
BASE = 62

def encode_base62(num: int) -> str:
    if num == 0:
        return ALPHABET[0]
    arr = []
    while num:
        num, rem = divmod(num, BASE)
        arr.append(ALPHABET[rem])
    arr.reverse()
    return ''.join(arr)

def decode_base62(s: str) -> int:
    num = 0
    for char in s:
        num = num * BASE + ALPHABET.index(char)
    return num

def generate_random_id(length: int = 7) -> str:
    """Generate a random Base62 string of given length."""
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))
```

```python src/utils/url_validator.py
"""
    URL validation with anti-SSRF checks.
"""
import ipaddress
from urllib.parse import urlparse
from fastapi import HTTPException, status
from src.config import settings

# Maximum URL length
MAX_URL_LENGTH = 2048

def validate_url(url: str) -> str:
    if not isinstance(url, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL must be a string")
    if len(url) > MAX_URL_LENGTH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"URL exceeds {MAX_URL_LENGTH} characters")
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL format")
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL must have scheme and host")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only HTTP/HTTPS allowed")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing hostname")
    # SSRF protection: block private/local addresses
    blocked = settings.blocked_hosts_list
    for block in blocked:
        if block in hostname:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Blocked host")
    # Also check if hostname resolves to private IP (basic check)
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Private IP not allowed")
    except ValueError:
        # Not an IP address; it's a domain name, skip
        pass
    return url
```

```python src/services/__init__.py
"""
    Business logic services.
"""
```

```python src/services/id_generator.py
"""
    Unique ID generation with collision retry.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.url_mapping import UrlMapping
from src.utils.base62 import generate_random_id

logger = logging.getLogger(__name__)
MAX_RETRIES = 3

async def generate_unique_id(db: AsyncSession, length: int = 7) -> str:
    """Generate a unique short ID, retrying on collision."""
    for attempt in range(MAX_RETRIES):
        short_id = generate_random_id(length)
        # Check uniqueness in DB
        stmt = select(UrlMapping.id).where(UrlMapping.id == short_id)
        result = await db.execute(stmt)
        if result.scalar() is None:
            return short_id
        logger.warning(f"ID collision for {short_id}, retry {attempt + 1}")
    raise RuntimeError("Failed to generate unique ID after multiple attempts")
```

```python src/services/url_shortener.py
"""
    URL shortening business logic.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as aioredis

from src.models.url_mapping import UrlMapping
from src.services.id_generator import generate_unique_id
from src.services.stats import sync_click_count
from src.config import settings
from src.schemas.shorten import ShortenResponse

logger = logging.getLogger(__name__)

async def create_short_url(
    db: AsyncSession,
    redis: aioredis.Redis,
    url: str,
    expires_at: Optional[datetime] = None,
) -> ShortenResponse:
    # Generate unique ID
    short_id = await generate_unique_id(db)
    now = datetime.now(timezone.utc)
    # Create DB entry
    db_entry = UrlMapping(
        id=short_id,
        original_url=url,
        created_at=now,
        expires_at=expires_at,
    )
    db.add(db_entry)
    await db.flush()  # Ensure it's persisted before cache
    # Cache in Redis
    await redis.set(
        f"url:{short_id}",
        url,
        ex=settings.CACHE_TTL_SECONDS,
    )
    short_url = f"{settings.BASE_URL}/{short_id}"
    return ShortenResponse(
        short_id=short_id,
        short_url=short_url,
        original_url=url,
        created_at=now,
        expires_at=expires_at,
    )

async def get_url_and_increment(
    db: AsyncSession,
    redis: aioredis.Redis,
    short_id: str,
) -> str:
    """
    Retrieve original URL and increment click counter.
    Returns the URL or raises 404 or 410.
    """
    # 1. Check cache
    cached_url = await redis.get(f"url:{short_id}")
    if cached_url:
        # Validate that DB record still exists and is active (cache could be stale)
        # We'll trust cache for speed, but check expiration later
        # Increment counter in Redis
        await redis.incr(f"stats:{short_id}")
        # Minimal check: if we suspect deletion/expiry, we can query DB in background.
        # For strict correctness, we must check DB when cache hit.
        # Architecture: "Поиск в Redis → при промахе — PostgreSQL". It implies cache may be stale.
        # We'll still validate expiration from DB if necessary. But for simplicity,
        # we'll rely on cache only for redirection, and handle expired/deleted in error response.
        # Actually we should check DB if expired/deleted to avoid redirecting after deletion.
        # I'll query DB briefly for is_deleted and expires_at.
        stmt = select(UrlMapping).where(UrlMapping.id == short_id)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry is None or entry.is_deleted:
            # Invalidate cache
            await redis.delete(f"url:{short_id}", f"stats:{short_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
        if entry.expires_at and entry.expires_at <= datetime.now(timezone.utc):
            await redis.delete(f"url:{short_id}", f"stats:{short_id}")
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short URL expired")
        # If we got here, cache is valid, proceed with redirect
        await redis.incr(f"stats:{short_id}")  # Already incremented? But we did earlier; skip or use existing count.
        # The earlier incr was already done. So we do nothing.
        return cached_url.decode()

    # 2. Cache miss: query DB
    stmt = select(UrlMapping).where(UrlMapping.id == short_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None or entry.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
    if entry.expires_at and entry.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short URL expired")
    # Cache the URL (with TTL)
    await redis.set(
        f"url:{short_id}",
        entry.original_url,
        ex=settings.CACHE_TTL_SECONDS,
    )
    # Increment counter
    await redis.incr(f"stats:{short_id}")
    return entry.original_url

async def delete_short_url(
    db: AsyncSession,
    redis: aioredis.Redis,
    short_id: str,
):
    stmt = select(UrlMapping).where(UrlMapping.id == short_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None or entry.is_deleted:
        raise HTTPException(status_code=404, detail="Short URL not found")
    # Soft delete
    entry.is_deleted = True
    db.add(entry)
    # Invalidate cache
    await redis.delete(f"url:{short_id}", f"stats:{short_id}")
    # Not raising, will return 204 in endpoint
```

```python src/services/stats.py
"""
    Statistics service: syncs Redis counter to DB and returns aggregated stats.
"""
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as aioredis

from src.models.url_mapping import UrlMapping
from src.schemas.stats import StatsResponse

logger = logging.getLogger(__name__)

async def sync_click_count(db: AsyncSession, redis: aioredis.Redis, short_id: str):
    """Flush Redis counter to PostgreSQL."""
    redis_key = f"stats:{short_id}"
    count_bytes = await redis.get(redis_key)
    if count_bytes is None:
        return
    try:
        count = int(count_bytes)
    except (ValueError, TypeError):
        return
    if count > 0:
        # Atomic update in DB
        stmt = (
            update(UrlMapping)
            .where(UrlMapping.id == short_id)
            .values(click_count=UrlMapping.click_count + count)
        )
        await db.execute(stmt)
        await db.flush()
        # Reset Redis counter
        await redis.delete(redis_key)

async def get_stats(
    db: AsyncSession,
    redis: aioredis.Redis,
    short_id: str,
) -> StatsResponse:
    # Sync Redis counter first
    await sync_click_count(db, redis, short_id)
    # Query DB for entry
    stmt = select(UrlMapping).where(UrlMapping.id == short_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    is_active = True
    if entry.is_deleted:
        is_active = False
    if entry.expires_at and entry.expires_at <= datetime.now(timezone.utc):
        is_active = False
    return StatsResponse(
        short_id=entry.id,
        original_url=entry.original_url,
        click_count=entry.click_count,
        created_at=entry.created_at,
        expires_at=entry.expires_at,
        is_active=is_active,
    )
```

```python src/api/__init__.py
"""
    API routers.
"""
```

```python src/api/router.py
"""
    Aggregate all routers.
"""
from fastapi import APIRouter
from src.api.shorten import router as shorten_router
from src.api.redirect import router as redirect_router
from src.api.stats import router as stats_router
from src.api.delete import router as delete_router

api_router = APIRouter()
api_router.include_router(shorten_router, tags=["shorten"])
api_router.include_router(redirect_router, tags=["redirect"])
api_router.include_router(stats_router, tags=["stats"])
api_router.include_router(delete_router, tags=["delete"])
```

```python src/api/shorten.py
"""
    POST /shorten endpoint.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from src.dependencies import get_db, get_redis
from src.schemas.shorten import ShortenRequest, ShortenResponse
from src.services.url_shortener import create_short_url

router = APIRouter()

@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    request: ShortenRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Create a short URL.
    Accepts JSON body with 'url' and optional 'expires_at'.
    Returns short ID and other details.
    """
    # Validation already done in Pydantic model
    try:
        response = await create_short_url(
            db=db,
            redis=redis,
            url=request.url,
            expires_at=request.expires_at,
        )
        return response
    except Exception as e:
        # Service functions raise HTTPException or propagate internal errors.
        # The global error handler will format the response.
        raise
```

```python src/api/redirect.py
"""
    GET /{id} endpoint.
"""
import re
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from src.dependencies import get_db, get_redis
from src.services.url_shortener import get_url_and_increment

router = APIRouter()

ID_PATTERN = re.compile(r"^[A-Za-z0-9]{7}$")

@router.get("/{short_id}", response_class=RedirectResponse)
async def redirect_to_original(
    short_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    """
    Redirect to the original URL.
    Increments click counter and returns 301 or 302.
    """
    if not ID_PATTERN.match(short_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")
    original_url = await get_url_and_increment(db, redis, short_id)
    # Use 301 for permanent, or 302? Architecture says 301. We'll follow that.
    return RedirectResponse(url=original_url, status_code=301)
```

```python src/api/stats.py
"""
    GET /stats/{id} endpoint.
"""
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from src.dependencies import get_db, get_redis
from src.schemas.stats import StatsResponse
from src.services.stats import get_stats

router = APIRouter()

ID_PATTERN = re.compile(r"^[A-Za-z0-9]{7}$")

@router.get("/stats/{short_id}", response_model=StatsResponse)
async def get_url_stats(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not ID_PATTERN.match(short_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")
    return await get_stats(db, redis, short_id)
```

```python src/api/delete.py
"""
    DELETE /{id} endpoint.
"""
import re
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from src.dependencies import get_db, get_redis
from src.services.url_shortener import delete_short_url

router = APIRouter()

ID_PATTERN = re.compile(r"^[A-Za-z0-9]{7}$")

@router.delete("/{short_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not ID_PATTERN.match(short_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")
    await delete_short_url(db, redis, short_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

```python src/middleware/__init__.py
"""
    Custom middlewares.
"""
```

```python src/middleware/request_id.py
"""
    Middleware adding X-Request-ID to each request.
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

```python src/middleware/rate_limiter.py
"""
    Sliding window rate limiter using Redis sorted set.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from fastapi import status
import redis.asyncio as aioredis

from src.dependencies import get_redis
from src.config import settings

logger = logging.getLogger(__name__)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    EXCLUDED_PATHS = ["/health", "/ready", "/docs", "/redoc", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for excluded paths
        path = request.url.path
        if path in self.EXCLUDED_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # Get client IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        redis: aioredis.Redis = await get_redis()
        key = f"ratelimit:{ip}"
        now = time.time()
        window = 60  # seconds
        max_requests = settings.RATE_LIMIT_PER_MINUTE

        # Remove outdated entries
        await redis.zremrangebyscore(key, 0, now - window)
        # Count current entries
        current = await redis.zcard(key)
        if current >= max_requests:
            retry_after = int(window - (now - float(await redis.zrange(key, 0, 0, withscores=True)[0][1]))) if current else window
            # Return 429
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests",
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )
        # Add current request timestamp with a unique score (to handle concurrent requests)
        await redis.zadd(key, {str(uuid.uuid4()): now})
        # Set expiry on key to clean up memory
        await redis.expire(key, window)

        response = await call_next(request)
        return response
```

```python src/middleware/error_handler.py
"""
    Global exception handler that formats errors as JSON with request ID.
"""
import logging
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint):
        try:
            return await call_next(request)
        except Exception as exc:
            # Extract request_id if available
            request_id = getattr(request.state, "request_id", None)
            return self.format_exception(exc, request_id)

    def format_exception(self, exc: Exception, request_id: str | None) -> JSONResponse:
        if isinstance(exc, StarletteHTTPException):
            status_code = exc.status_code
            detail = exc.detail
            code = "HTTP_ERROR"
            # Map common HTTP codes to named codes
            if status_code == 404:
                code = "NOT_FOUND"
            elif status_code == 410:
                code = "GONE"
            elif status_code == 400:
                code = "BAD_REQUEST"
            elif status_code == 429:
                code = "RATE_LIMIT_EXCEEDED"
            message = str(detail) if isinstance(detail, str) else detail.get("detail", "Unexpected error")
        elif isinstance(exc, RequestValidationError):
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            code = "VALIDATION_ERROR"
            message = str(exc)
        else:
            logger.exception("Unhandled exception")
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            code = "INTERNAL_ERROR"
            message = "An unexpected error occurred"

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": request_id,
                }
            },
        )
```

```python tests/__init__.py
"""
    Test suite for URL Shortener.
"""
```

```python tests/conftest.py
"""
    Pytest fixtures: test application, database session, Redis mock.
"""
import asyncio
from typing import AsyncGenerator, Generator
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from src.main import app
from src.dependencies import get_db, get_redis
from src.models import Base
import fakeredis.aioredis  # For async fake Redis

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite://"

@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="session")
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(engine, create_tables) -> AsyncGenerator[AsyncSession, None]:
    connection = await engine.connect()
    trans = await connection.begin()
    session = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)()
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()

@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator:
    # Use fake Redis
    redis = fakeredis.aioredis.FakeRedis()
    yield redis
    await redis.flushall()
    await redis.aclose()

@pytest_asyncio.fixture
async def async_client(db_session, redis_client) -> AsyncGenerator[AsyncClient, None]:
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: redis_client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
```

Now test files:

```python tests/test_shorten.py
"""
    Tests for POST /shorten endpoint.
"""
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_shorten_valid_url(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={"url": "https://example.com/long/path"})
    assert resp.status_code == 201
    data = resp.json()
    assert "short_id" in data
    assert data["original_url"] == "https://example.com/long/path"
    assert data["short_url"].startswith("https://sho.rt/")

@pytest.mark.asyncio
async def test_shorten_invalid_url(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={"url": "not-a-url"})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_shorten_blocked_host(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={"url": "http://localhost"})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_shorten_with_expiry(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={
        "url": "https://example.com",
        "expires_at": "2025-12-31T23:59:59Z"
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["expires_at"] is not None
```

```python tests/test_redirect.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_redirect_valid_id(async_client: AsyncClient):
    # First create a short URL
    create_resp = await async_client.post("/shorten", json={"url": "https://example.com"})
    short_id = create_resp.json()["short_id"]
    # Then redirect
    resp = await async_client.get(f"/{short_id}", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["location"] == "https://example.com"

@pytest.mark.asyncio
async def test_redirect_not_found(async_client: AsyncClient):
    resp = await async_client.get("/abc1234", follow_redirects=False)
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_redirect_id_format(async_client: AsyncClient):
    resp = await async_client.get("/short", follow_redirects=False)
    assert resp.status_code == 400
```

```python tests/test_stats.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_stats(async_client: AsyncClient):
    create_resp = await async_client.post("/shorten", json={"url": "https://example.com"})
    short_id = create_resp.json()["short_id"]
    # Simulate a click
    await async_client.get(f"/{short_id}", follow_redirects=False)
    # Get stats
    stats_resp = await async_client.get(f"/stats/{short_id}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["click_count"] == 1
    assert data["is_active"] is True
```

```python tests/test_delete.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_delete(async_client: AsyncClient):
    create_resp = await async_client.post("/shorten", json={"url": "https://example.com"})
    short_id = create_resp.json()["short_id"]
    # Delete
    del_resp = await async_client.delete(f"/{short_id}")
    assert del_resp.status_code == 204
    # Try redirect -> 404
    redirect_resp = await async_client.get(f"/{short_id}", follow_redirects=False)
    assert redirect_resp.status_code == 404
```

```python tests/test_rate_limiter.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_rate_limit(async_client: AsyncClient):
    # Make requests up to limit; rate limit per minute in test is 100 (default)
    # To trigger, we would need >100 requests. For a quick test, we can override setting.
    # Since conftest imports app, we can temporarily overwrite config setting.
    from src.config import settings
    original_limit = settings.RATE_LIMIT_PER_MINUTE
    settings.RATE_LIMIT_PER_MINUTE = 2
    # Send 3 requests
    responses = []
    for _ in range(3):
        resp = await async_client.post("/shorten", json={"url": "https://example.com"})
        responses.append(resp.status_code)
    settings.RATE_LIMIT_PER_MINUTE = original_limit
    assert responses[0] == 201
    assert responses[1] == 201
    assert responses[2] == 429
```

```python tests/test_url_validator.py
import pytest
from src.utils.url_validator import validate_url

def test_valid_url():
    assert validate_url("https://example.com")

def test_invalid_url():
    with pytest.raises(Exception):
        validate_url("")
    with pytest.raises(Exception):
        validate_url("ftp://example.com")
```

```python tests/test_id_generator.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.id_generator import generate_unique_id

@pytest.mark.asyncio
async def test_generates_unique_id(db_session: AsyncSession):
    id1 = await generate_unique_id(db_session)
    id2 = await generate_unique_id(db_session)
    assert len(id1) == 7
    assert id1 != id2
```

That's all the files. We'll now compile the final answer with each file in a markdown block. We'll also make sure imports are correct and code is self-consistent. In the middleware error handler, need to import from starlette.exceptions HTTPException. It's already imported. Also in stats service, need `HTTPException` import; I added it inline. I need to add it to imports. We'll ensure all files have necessary imports.

Potential issues:
- In rate_limiter, we used `uuid` but didn't import it; we'll add import.
- In `src/api/delete.py`, we missed `HTTPException` import, but we just return Response, so it's okay. But we raise HTTPException in service, and we let it propagate.
- In `src/services/url_shortener.py`, we used `HTTPException` but imported it.
- In `src/api/redirect.py`, `ID_PATTERN` defined globally.

Let's double-check that all dependencies are used correctly: `fakeredis` is imported as `fakeredis.aioredis.FakeRedis`. That's correct.

Now present the final answer. It will be very long. We'll use proper markdown code fences with file paths```python pyproject.toml
[project]
name = "url-shortener"
version = "0.1.0"
description = "URL Shortener microservice"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.27.0",
    "sqlalchemy[asyncio]>=2.0.25",
    "asyncpg>=0.29.0",
    "redis[hiredis]>=5.0.1",
    "pydantic-settings>=2.1.0",
    "alembic>=1.13.1",
    "python-dotenv>=1.0.1"
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.3",
    "httpx>=0.26.0",
    "fakeredis[lua]>=2.20.0",
    "aiosqlite>=0.19.0"
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

```bash .env.example
APP_HOST=0.0.0.0
APP_PORT=8000
BASE_URL=https://sho.rt
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/urlshortener
REDIS_URL=redis://localhost:6379/0
RATE_LIMIT_PER_MINUTE=100
CACHE_TTL_SECONDS=3600
SHUTDOWN_TIMEOUT_SECONDS=30
LOG_LEVEL=INFO
BLOCKED_HOSTS=localhost,127.0.0.1,10.,192.168.
```

```dockerfile Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
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
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    restart: unless-stopped

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
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d urlshortener"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

```ini alembic.ini
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

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from src.config import settings
from src.models import Base  # Import all models so metadata is populated

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online():
    url = settings.DATABASE_URL
    connectable = create_async_engine(url)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

```python alembic/versions/001_initial.py
"""initial

Revision ID: 001
Revises:
Create Date: 2025-03-15

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'url_mapping',
        sa.Column('id', sa.String(7), primary_key=True),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('click_count', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    )
    op.create_index('idx_original_url', 'url_mapping', ['original_url'])
    op.create_index('idx_expires_at', 'url_mapping', ['expires_at'], postgresql_where=sa.text('is_deleted = FALSE'))

def downgrade():
    op.drop_index('idx_expires_at')
    op.drop_index('idx_original_url')
    op.drop_table('url_mapping')
```

```python src/__init__.py
"""
    URL Shortener microservice.

    Strictly follows architecture document: provides API for shortening,
    redirecting, retrieving stats, and deleting URLs.
"""
```

```python src/main.py
"""
    FastAPI application entry point.

    Sets up all middlewares, routers, and startup/shutdown events.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from sqlalchemy import text

from src.api.router import api_router
from src.config import settings
from src.db.postgres import engine, async_session_maker
from src.db.redis import get_redis
from src.middleware.error_handler import ErrorHandlingMiddleware
from src.middleware.rate_limiter import RateLimiterMiddleware
from src.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        return response

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Application starting up")
    async with engine.begin() as conn:
        # Verify DB connectivity (optional)
        pass
    yield
    logger.info("Application shutting down")
    await engine.dispose()
    redis = await get_redis()
    await redis.close()

app = FastAPI(
    title="URL Shortener",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Middleware order (outermost first)
app.add_middleware(ErrorHandlingMiddleware)
app.add_middleware(RateLimiterMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1000)

app.include_router(api_router)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {"status": "not ready"}, 503
```

```python src/config.py
"""
    Application settings using pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    BASE_URL: str = "https://sho.rt"
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/urlshortener"
    REDIS_URL: str = "redis://localhost:6379/0"
    RATE_LIMIT_PER_MINUTE: int = 100
    CACHE_TTL_SECONDS: int = 3600
    SHUTDOWN_TIMEOUT_SECONDS: int = 30
    LOG_LEVEL: str = "INFO"

    BLOCKED_HOSTS: str = "localhost,127.0.0.1,10.,192.168."

    @property
    def blocked_hosts_list(self) -> list[str]:
        return [h.strip() for h in self.BLOCKED_HOSTS.split(",") if h.strip()]

settings = Settings()
```

```python src/db/postgres.py
"""
    PostgreSQL async engine and session factory using SQLAlchemy 2.0.
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from src.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    """Dependency yielding an async database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

```python src/db/redis.py
"""
    Redis async client factory and connection pool.
"""
import logging

import redis.asyncio as aioredis
from redis.asyncio.connection import ConnectionPool

from src.config import settings

logger = logging.getLogger(__name__)

pool: ConnectionPool | None = None

async def create_redis_pool() -> ConnectionPool:
    global pool
    if pool is None:
        pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=20,
        )
        logger.info("Redis connection pool created")
    return pool

async def get_redis() -> aioredis.Redis:
    """Dependency providing Redis client from the pool."""
    p = await create_redis_pool()
    return aioredis.Redis(connection_pool=p)

async def close_redis_pool():
    global pool
    if pool:
        await pool.disconnect()
        pool = None
```

```python src/dependencies.py
"""
    Dependency injection container; re-exports commonly used dependencies.
"""
from src.db.postgres import get_db
from src.db.redis import get_redis
```

```python src/models/__init__.py
"""
    SQLAlchemy models package.
"""
from src.models.url_mapping import UrlMapping

__all__ = ["UrlMapping"]

# For Alembic metadata target
Base = UrlMapping.metadata
```

```python src/models/url_mapping.py
"""
    SQLAlchemy ORM model for url_mapping table.
"""
from datetime import datetime

from sqlalchemy import String, Text, DateTime, Boolean, BigInteger, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class UrlMapping(Base):
    __tablename__ = "url_mapping"

    id: Mapped[str] = mapped_column(String(7), primary_key=True)
    original_url: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean(), server_default="false", nullable=False)
    click_count: Mapped[int] = mapped_column(BigInteger(), server_default="0", nullable=False)
```

```python src/schemas/__init__.py
"""
    Pydantic schemas package.
"""
```

```python src/schemas/errors.py
"""
    Standard error response schema.
"""
from pydantic import BaseModel

class ErrorResponse(BaseModel):
    code: str
    message: str
    request_id: str | None = None
```

```python src/schemas/shorten.py
"""
    Schemas for /shorten endpoint.
"""
from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Optional

class ShortenRequest(BaseModel):
    url: str
    expires_at: Optional[datetime] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        from src.utils.url_validator import validate_url
        return validate_url(v)

class ShortenResponse(BaseModel):
    short_id: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
```

```python src/schemas/stats.py
"""
    Schemas for /stats/{id} endpoint.
"""
from datetime import datetime
from pydantic import BaseModel

class StatsResponse(BaseModel):
    short_id: str
    original_url: str
    click_count: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
```

```python src/utils/__init__.py
"""
    Utility modules.
"""
```

```python src/utils/base62.py
"""
    Base62 encoding/decoding.
    Uses characters A-Z, a-z, 0-9.
"""
import string
import secrets

ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits
BASE = 62

def encode_base62(num: int) -> str:
    if num == 0:
        return ALPHABET[0]
    arr = []
    while num:
        num, rem = divmod(num, BASE)
        arr.append(ALPHABET[rem])
    arr.reverse()
    return ''.join(arr)

def decode_base62(s: str) -> int:
    num = 0
    for char in s:
        num = num * BASE + ALPHABET.index(char)
    return num

def generate_random_id(length: int = 7) -> str:
    """Generate a random Base62 string of given length."""
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))
```

```python src/utils/url_validator.py
"""
    URL validation with anti-SSRF checks.
"""
import ipaddress
from urllib.parse import urlparse
from fastapi import HTTPException, status
from src.config import settings

MAX_URL_LENGTH = 2048

def validate_url(url: str) -> str:
    if not isinstance(url, str):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL must be a string")
    if len(url) > MAX_URL_LENGTH:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"URL exceeds {MAX_URL_LENGTH} characters")
    try:
        parsed = urlparse(url)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL format")
    if not parsed.scheme or not parsed.netloc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="URL must have scheme and host")
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only HTTP/HTTPS allowed")
    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing hostname")
    # SSRF protection: block private/local addresses
    blocked = settings.blocked_hosts_list
    for block in blocked:
        if block in hostname:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Blocked host")
    try:
        addr = ipaddress.ip_address(hostname)
        if addr.is_private or addr.is_loopback or addr.is_link_local:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Private IP not allowed")
    except ValueError:
        pass
    return url
```

```python src/services/__init__.py
"""
    Business logic services.
"""
```

```python src/services/id_generator.py
"""
    Unique ID generation with collision retry.
"""
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.url_mapping import UrlMapping
from src.utils.base62 import generate_random_id

logger = logging.getLogger(__name__)
MAX_RETRIES = 3

async def generate_unique_id(db: AsyncSession, length: int = 7) -> str:
    """Generate a unique short ID, retrying on collision."""
    for attempt in range(MAX_RETRIES):
        short_id = generate_random_id(length)
        stmt = select(UrlMapping.id).where(UrlMapping.id == short_id)
        result = await db.execute(stmt)
        if result.scalar() is None:
            return short_id
        logger.warning(f"ID collision for {short_id}, retry {attempt + 1}")
    raise RuntimeError("Failed to generate unique ID after multiple attempts")
```

```python src/services/url_shortener.py
"""
    URL shortening business logic.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as aioredis

from src.models.url_mapping import UrlMapping
from src.services.id_generator import generate_unique_id
from src.config import settings
from src.schemas.shorten import ShortenResponse

logger = logging.getLogger(__name__)

async def create_short_url(
    db: AsyncSession,
    redis: aioredis.Redis,
    url: str,
    expires_at: Optional[datetime] = None,
) -> ShortenResponse:
    short_id = await generate_unique_id(db)
    now = datetime.now(timezone.utc)
    entry = UrlMapping(
        id=short_id,
        original_url=url,
        created_at=now,
        expires_at=expires_at,
    )
    db.add(entry)
    await db.flush()
    await redis.set(f"url:{short_id}", url, ex=settings.CACHE_TTL_SECONDS)
    short_url = f"{settings.BASE_URL}/{short_id}"
    return ShortenResponse(
        short_id=short_id,
        short_url=short_url,
        original_url=url,
        created_at=now,
        expires_at=expires_at,
    )

async def get_url_and_increment(
    db: AsyncSession,
    redis: aioredis.Redis,
    short_id: str,
) -> str:
    # 1. Try cache
    cached_url = await redis.get(f"url:{short_id}")
    if cached_url:
        # Still verify DB for deletion/expiry to avoid serving stale cache
        stmt = select(UrlMapping).where(UrlMapping.id == short_id)
        result = await db.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry is None or entry.is_deleted:
            await redis.delete(f"url:{short_id}", f"stats:{short_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
        if entry.expires_at and entry.expires_at <= datetime.now(timezone.utc):
            await redis.delete(f"url:{short_id}", f"stats:{short_id}")
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short URL expired")
        # Increment counter in Redis
        await redis.incr(f"stats:{short_id}")
        return cached_url.decode()

    # 2. Cache miss: query DB
    stmt = select(UrlMapping).where(UrlMapping.id == short_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None or entry.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
    if entry.expires_at and entry.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short URL expired")
    await redis.set(f"url:{short_id}", entry.original_url, ex=settings.CACHE_TTL_SECONDS)
    await redis.incr(f"stats:{short_id}")
    return entry.original_url

async def delete_short_url(
    db: AsyncSession,
    redis: aioredis.Redis,
    short_id: str,
):
    stmt = select(UrlMapping).where(UrlMapping.id == short_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None or entry.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
    entry.is_deleted = True
    db.add(entry)
    await redis.delete(f"url:{short_id}", f"stats:{short_id}")
```

```python src/services/stats.py
"""
    Statistics service: syncs Redis counter to DB and returns aggregated stats.
"""
import logging
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as aioredis

from src.models.url_mapping import UrlMapping
from src.schemas.stats import StatsResponse

logger = logging.getLogger(__name__)

async def sync_click_count(db: AsyncSession, redis: aioredis.Redis, short_id: str):
    redis_key = f"stats:{short_id}"
    count_bytes = await redis.get(redis_key)
    if count_bytes is None:
        return
    try:
        count = int(count_bytes)
    except (ValueError, TypeError):
        return
    if count > 0:
        stmt = (
            update(UrlMapping)
            .where(UrlMapping.id == short_id)
            .values(click_count=UrlMapping.click_count + count)
        )
        await db.execute(stmt)
        await db.flush()
        await redis.delete(redis_key)

async def get_stats(
    db: AsyncSession,
    redis: aioredis.Redis,
    short_id: str,
) -> StatsResponse:
    await sync_click_count(db, redis, short_id)
    stmt = select(UrlMapping).where(UrlMapping.id == short_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    is_active = True
    if entry.is_deleted:
        is_active = False
    if entry.expires_at and entry.expires_at <= datetime.now(timezone.utc):
        is_active = False
    return StatsResponse(
        short_id=entry.id,
        original_url=entry.original_url,
        click_count=entry.click_count,
        created_at=entry.created_at,
        expires_at=entry.expires_at,
        is_active=is_active,
    )
```

```python src/api/__init__.py
"""
    API routers.
"""
```

```python src/api/router.py
"""
    Aggregate all routers.
"""
from fastapi import APIRouter
from src.api.shorten import router as shorten_router
from src.api.redirect import router as redirect_router
from src.api.stats import router as stats_router
from src.api.delete import router as delete_router

api_router = APIRouter()
api_router.include_router(shorten_router, tags=["shorten"])
api_router.include_router(redirect_router, tags=["redirect"])
api_router.include_router(stats_router, tags=["stats"])
api_router.include_router(delete_router, tags=["delete"])
```

```python src/api/shorten.py
"""
    POST /shorten endpoint.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from src.dependencies import get_db, get_redis
from src.schemas.shorten import ShortenRequest, ShortenResponse
from src.services.url_shortener import create_short_url

router = APIRouter()

@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    request: ShortenRequest,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    return await create_short_url(db, redis, request.url, request.expires_at)
```

```python src/api/redirect.py
"""
    GET /{id} endpoint.
"""
import re
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from src.dependencies import get_db, get_redis
from src.services.url_shortener import get_url_and_increment

router = APIRouter()
ID_PATTERN = re.compile(r"^[A-Za-z0-9]{7}$")

@router.get("/{short_id}", response_class=RedirectResponse)
async def redirect_to_original(
    short_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not ID_PATTERN.match(short_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")
    original_url = await get_url_and_increment(db, redis, short_id)
    return RedirectResponse(url=original_url, status_code=301)
```

```python src/api/stats.py
"""
    GET /stats/{id} endpoint.
"""
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from src.dependencies import get_db, get_redis
from src.schemas.stats import StatsResponse
from src.services.stats import get_stats

router = APIRouter()
ID_PATTERN = re.compile(r"^[A-Za-z0-9]{7}$")

@router.get("/stats/{short_id}", response_model=StatsResponse)
async def get_url_stats(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not ID_PATTERN.match(short_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")
    return await get_stats(db, redis, short_id)
```

```python src/api/delete.py
"""
    DELETE /{id} endpoint.
"""
import re
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as aioredis

from src.dependencies import get_db, get_redis
from src.services.url_shortener import delete_short_url

router = APIRouter()
ID_PATTERN = re.compile(r"^[A-Za-z0-9]{7}$")

@router.delete("/{short_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis: aioredis.Redis = Depends(get_redis),
):
    if not ID_PATTERN.match(short_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")
    await delete_short_url(db, redis, short_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
```

```python src/middleware/__init__.py
"""
    Custom middlewares.
"""
```

```python src/middleware/request_id.py
"""
    Middleware adding X-Request-ID to each request.
"""
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

```python src/middleware/rate_limiter.py
"""
    Sliding window rate limiter using Redis sorted set.
"""
import time
import logging
import uuid
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from fastapi import status
import redis.asyncio as aioredis

from src.dependencies import get_redis
from src.config import settings

logger = logging.getLogger(__name__)

class RateLimiterMiddleware(BaseHTTPMiddleware):
    EXCLUDED_PATHS = ["/health", "/ready", "/docs", "/redoc", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path
        if path in self.EXCLUDED_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        forwarded = request.headers.get("X-Forwarded-For")
        ip = forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown")
        redis: aioredis.Redis = await get_redis()
        key = f"ratelimit:{ip}"
        now = time.time()
        window = 60
        max_requests = settings.RATE_LIMIT_PER_MINUTE

        # Remove outdated entries
        await redis.zremrangebyscore(key, 0, now - window)
        current = await redis.zcard(key)
        if current >= max_requests:
            retry_after = window
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": "Too many requests",
                        "request_id": getattr(request.state, "request_id", None),
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )
        await redis.zadd(key, {str(uuid.uuid4()): now})
        await redis.expire(key, window)

        response = await call_next(request)
        return response
```

```python src/middleware/error_handler.py
"""
    Global exception handler that formats errors as JSON with request ID.
"""
import logging
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            request_id = getattr(request.state, "request_id", None)
            return self.format_exception(exc, request_id)

    def format_exception(self, exc: Exception, request_id: str | None) -> JSONResponse:
        if isinstance(exc, StarletteHTTPException):
            status_code = exc.status_code
            detail = exc.detail
            code = "HTTP_ERROR"
            if status_code == 404:
                code = "NOT_FOUND"
            elif status_code == 410:
                code = "GONE"
            elif status_code == 400:
                code = "BAD_REQUEST"
            elif status_code == 429:
                code = "RATE_LIMIT_EXCEEDED"
            message = str(detail) if isinstance(detail, str) else detail.get("detail", "Unexpected error")
        elif isinstance(exc, RequestValidationError):
            status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            code = "VALIDATION_ERROR"
            message = str(exc)
        else:
            logger.exception("Unhandled exception")
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            code = "INTERNAL_ERROR"
            message = "An unexpected error occurred"

        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": code,
                    "message": message,
                    "request_id": request_id,
                }
            },
        )
```

```python tests/__init__.py
"""
    Test suite for URL Shortener.
"""
```

```python tests/conftest.py
"""
    Pytest fixtures: test application, database session, Redis mock.
"""
from typing import AsyncGenerator
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import StaticPool

from src.main import app
from src.dependencies import get_db, get_redis
from src.models import Base
import fakeredis.aioredis

TEST_DATABASE_URL = "sqlite+aiosqlite://"

@pytest_asyncio.fixture(scope="session")
async def engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture(scope="session")
async def create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest_asyncio.fixture
async def db_session(engine, create_tables) -> AsyncGenerator[AsyncSession, None]:
    connection = await engine.connect()
    trans = await connection.begin()
    session = async_sessionmaker(bind=connection, class_=AsyncSession, expire_on_commit=False)()
    try:
        yield session
    finally:
        await session.close()
        await trans.rollback()
        await connection.close()

@pytest_asyncio.fixture
async def redis_client() -> AsyncGenerator:
    redis = fakeredis.aioredis.FakeRedis()
    yield redis
    await redis.flushall()
    await redis.aclose()

@pytest_asyncio.fixture
async def async_client(db_session, redis_client) -> AsyncGenerator[AsyncClient, None]:
    app.dependency_overrides[get_db] = lambda: db_session
    app.dependency_overrides[get_redis] = lambda: redis_client
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
```

```python tests/test_shorten.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_shorten_valid_url(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={"url": "https://example.com/long/path"})
    assert resp.status_code == 201
    data = resp.json()
    assert "short_id" in data
    assert data["original_url"] == "https://example.com/long/path"

@pytest.mark.asyncio
async def test_shorten_invalid_url(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={"url": "not-a-url"})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_shorten_blocked_host(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={"url": "http://localhost"})
    assert resp.status_code == 400

@pytest.mark.asyncio
async def test_shorten_with_expiry(async_client: AsyncClient):
    resp = await async_client.post("/shorten", json={
        "url": "https://example.com",
        "expires_at": "2025-12-31T23:59:59Z"
    })
    assert resp.status_code == 201
    assert resp.json()["expires_at"] is not None
```

```python tests/test_redirect.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_redirect_valid_id(async_client: AsyncClient):
    create_resp = await async_client.post("/shorten", json={"url": "https://example.com"})
    short_id = create_resp.json()["short_id"]
    resp = await async_client.get(f"/{short_id}", follow_redirects=False)
    assert resp.status_code == 301
    assert resp.headers["location"] == "https://example.com"

@pytest.mark.asyncio
async def test_redirect_not_found(async_client: AsyncClient):
    resp = await async_client.get("/abc1234", follow_redirects=False)
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_redirect_id_format(async_client: AsyncClient):
    resp = await async_client.get("/short", follow_redirects=False)
    assert resp.status_code == 400
```

```python tests/test_stats.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_stats(async_client: AsyncClient):
    create_resp = await async_client.post("/shorten", json={"url": "https://example.com"})
    short_id = create_resp.json()["short_id"]
    await async_client.get(f"/{short_id}", follow_redirects=False)
    stats_resp = await async_client.get(f"/stats/{short_id}")
    assert stats_resp.status_code == 200
    data = stats_resp.json()
    assert data["click_count"] == 1
    assert data["is_active"] is True
```

```python tests/test_delete.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_delete(async_client: AsyncClient):
    create_resp = await async_client.post("/shorten", json={"url": "https://example.com"})
    short_id = create_resp.json()["short_id"]
    del_resp = await async_client.delete(f"/{short_id}")
    assert del_resp.status_code == 204
    redirect_resp = await async_client.get(f"/{short_id}", follow_redirects=False)
    assert redirect_resp.status_code == 404
```

```python tests/test_rate_limiter.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_rate_limit(async_client: AsyncClient):
    from src.config import settings
    original_limit = settings.RATE_LIMIT_PER_MINUTE
    settings.RATE_LIMIT_PER_MINUTE = 2
    responses = []
    for _ in range(3):
        resp = await async_client.post("/shorten", json={"url": "https://example.com"})
        responses.append(resp.status_code)
    settings.RATE_LIMIT_PER_MINUTE = original_limit
    assert responses[0] == 201
    assert responses[1] == 201
    assert responses[2] == 429
```

```python tests/test_url_validator.py
import pytest
from src.utils.url_validator import validate_url

def test_valid_url():
    assert validate_url("https://example.com") == "https://example.com"

def test_invalid_url():
    with pytest.raises(Exception):
        validate_url("")
    with pytest.raises(Exception):
        validate_url("ftp://example.com")
```

```python tests/test_id_generator.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.id_generator import generate_unique_id

@pytest.mark.asyncio
async def test_generates_unique_id(db_session: AsyncSession):
    id1 = await generate_unique_id(db_session)
    id2 = await generate_unique_id(db_session)
    assert len(id1) == 7
    assert id1 != id2
```