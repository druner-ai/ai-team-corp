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
# app/__init__.py
# app package
```

```python
# app/main.py
"""
FastAPI application entry point.
Sets up middleware, routers, and lifespan events.
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine, AsyncSessionLocal
from app.exceptions.handlers import register_exception_handlers
from app.middleware.rate_limiter import limiter
from app.routers import health, redirect, shorten, stats, delete
from app.redis_client import redis_client
from app.services.sync_service import SyncService


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown events."""
    # Start background click counter sync
    sync_service = SyncService()
    task = asyncio.create_task(sync_service.start(redis_client, AsyncSessionLocal))
    yield
    # Shutdown: cancel background task, close DB, close Redis
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass
    await engine.dispose()
    await redis_client.aclose()


app = FastAPI(
    title="URL Shortener",
    description="Microservice for shortening URLs with caching and statistics",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: allow only GET and OPTIONS for redirects (as per architecture, but open for brevity)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# Rate limiter middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Register custom exception handlers
register_exception_handlers(app)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(shorten.router, prefix="/shorten", tags=["shorten"])
app.include_router(redirect.router, tags=["redirect"])
app.include_router(stats.router, prefix="/stats", tags=["stats"])
app.include_router(delete.router, tags=["delete"])
```

```python
# app/config.py
"""
Application settings loaded from environment/.env file.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        alias="REDIS_URL",
    )
    base_url: str = Field(
        default="http://localhost:8000",
        alias="BASE_URL",
    )
    short_code_length: int = Field(
        default=6,
        ge=4,
        le=10,
        alias="SHORT_CODE_LENGTH",
    )
    cache_ttl_seconds: int = Field(
        default=3600,
        alias="CACHE_TTL_SECONDS",
    )
    rate_limit_shorten: str = Field(
        default="10/minute",
        alias="RATE_LIMIT_SHORTEN",
    )
    rate_limit_redirect: str = Field(
        default="100/minute",
        alias="RATE_LIMIT_REDIRECT",
    )
    rate_limit_stats: str = Field(
        default="30/minute",
        alias="RATE_LIMIT_STATS",
    )
    rate_limit_delete: str = Field(
        default="10/minute",
        alias="RATE_LIMIT_DELETE",
    )
    sync_interval_seconds: int = Field(
        default=300,
        alias="SYNC_INTERVAL_SECONDS",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
```

```python
# app/database.py
"""
Async SQLAlchemy engine and session factory.
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

class Base(DeclarativeBase):
    pass

async def get_async_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

```python
# app/redis_client.py
"""
Redis async client factory using a shared global client.
"""
import redis.asyncio as aioredis
from app.config import settings

redis_client = aioredis.Redis.from_url(settings.redis_url, max_connections=10)

async def get_redis_client() -> aioredis.Redis:
    return redis_client
```

```python
# app/dependencies.py
# Re-export get_async_session for convenient imports by routers
from app.database import get_async_session
```

```python
# app/models/__init__.py
from app.models.url import URLRecord

__all__ = ["URLRecord"]
```

```python
# app/models/url.py
"""
SQLAlchemy ORM model for the `urls` table.
"""
import uuid
from sqlalchemy import String, Text, Boolean, BigInteger, TIMESTAMP, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base
from datetime import datetime

class URLRecord(Base):
    __tablename__ = "urls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        default=uuid.uuid4,
    )
    short_code: Mapped[str] = mapped_column(
        String(6), unique=True, nullable=False
    )
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, server_default=func.false(), nullable=False
    )
    click_count: Mapped[int] = mapped_column(
        BigInteger, server_default=func.text("0"), nullable=False
    )
    last_clicked_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
```

```python
# app/schemas/__init__.py
from app.schemas.url import ShortenRequest, ShortenResponse, StatsResponse
from app.schemas.common import ErrorResponse, HealthResponse

__all__ = [
    "ShortenRequest",
    "ShortenResponse",
    "StatsResponse",
    "ErrorResponse",
    "HealthResponse",
]
```

```python
# app/schemas/common.py
"""
Common response models for errors and health check.
"""
from pydantic import BaseModel
from typing import Any, Optional

class ErrorResponse(BaseModel):
    detail: str
    error_code: str = "error"
    status_code: int = 500
    extra: Optional[dict[str, Any]] = None

class HealthResponse(BaseModel):
    status: str
    db_connected: bool
    redis_connected: bool
    version: str = "1.0.0"
```

```python
# app/schemas/url.py
"""
Pydantic models for URL shortening requests and responses.
"""
from pydantic import BaseModel, HttpUrl, field_serializer, field_validator
from datetime import datetime
from typing import Optional
from app.utils.url_validator import validate_url_no_ssrf

class ShortenRequest(BaseModel):
    url: HttpUrl
    expires_at: Optional[datetime] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: HttpUrl) -> HttpUrl:
        validate_url_no_ssrf(str(v))
        return v

class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None

    @field_serializer("created_at")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()

    @field_serializer("expires_at")
    def serialize_expires_at(self, dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None

class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    click_count: int
    last_clicked_at: Optional[datetime]
    is_active: bool

    @field_serializer("created_at")
    def serialize_created(self, dt: datetime) -> str:
        return dt.isoformat()

    @field_serializer("last_clicked_at")
    def serialize_last_clicked(self, dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None
```

```python
# app/repositories/__init__.py
from app.repositories.url_repository import URLRepository
from app.repositories.cache_repository import CacheRepository

__all__ = ["URLRepository", "CacheRepository"]
```

```python
# app/repositories/url_repository.py
"""
Repository for PostgreSQL URL operations.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.url import URLRecord
from typing import Optional

class URLRepository:
    """CRUD operations for the `urls` table."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        short_code: str,
        original_url: str,
        expires_at: Optional[datetime] = None,
    ) -> URLRecord:
        record = URLRecord(
            short_code=short_code,
            original_url=original_url,
            expires_at=expires_at,
        )
        self.session.add(record)
        await self.session.commit()
        await self.session.refresh(record)
        return record

    async def get_by_short_code(self, short_code: str) -> Optional[URLRecord]:
        """Get active (not deleted) record by short_code."""
        stmt = select(URLRecord).where(
            URLRecord.short_code == short_code,
            URLRecord.is_deleted == False,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def exists_by_short_code(self, short_code: str) -> bool:
        """Check if any record (including soft-deleted) exists for a short_code."""
        stmt = select(URLRecord.id).where(URLRecord.short_code == short_code)
        result = await self.session.execute(stmt)
        return result.scalar() is not None

    async def update_click_and_last_access(self, record: URLRecord) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(URLRecord)
            .where(URLRecord.id == record.id)
            .values(
                click_count=URLRecord.click_count + 1,
                last_clicked_at=now,
            )
        )
        await self.session.execute(stmt)
        record.click_count += 1
        record.last_clicked_at = now
        await self.session.commit()

    async def update_click_and_last_access_by_short_code(self, short_code: str, clicks: int) -> None:
        now = datetime.now(timezone.utc)
        stmt = (
            update(URLRecord)
            .where(URLRecord.short_code == short_code)
            .values(
                click_count=URLRecord.click_count + clicks,
                last_clicked_at=now,
            )
        )
        await self.session.execute(stmt)

    async def soft_delete(self, record: URLRecord) -> None:
        record.is_deleted = True
        await self.session.commit()

    async def get_by_id(self, url_id: uuid.UUID) -> Optional[URLRecord]:
        stmt = select(URLRecord).where(URLRecord.id == url_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def bulk_update_click_counts(self, updates: dict[str, int]) -> None:
        for short_code, clicks in updates.items():
            stmt = (
                update(URLRecord)
                .where(URLRecord.short_code == short_code)
                .values(click_count=URLRecord.click_count + clicks)
            )
            await self.session.execute(stmt)
        await self.session.commit()
```

```python
# app/repositories/cache_repository.py
"""
Redis cache repository for short URL data and click counters.
"""
import redis.asyncio as aioredis
from typing import Optional, Dict
from datetime import datetime, timezone
from app.config import settings

class CacheRepository:
    def __init__(self, client: aioredis.Redis):
        self.client = client
        self.ttl = settings.cache_ttl_seconds

    def _key(self, short_code: str) -> str:
        return f"url:{short_code}"

    async def get_cached_url(self, short_code: str) -> Optional[Dict[str, str]]:
        data = await self.client.hgetall(self._key(short_code))
        if data:
            return {key.decode(): value.decode() for key, value in data.items()}
        return None

    async def set_cached_url(
        self,
        short_code: str,
        original_url: str,
        created_at: str,
        expires_at: Optional[str] = None,
        is_deleted: bool = False,
    ) -> None:
        key = self._key(short_code)
        mapping = {
            "original_url": original_url,
            "created_at": created_at,
            "is_deleted": str(int(is_deleted)),
        }
        if expires_at:
            mapping["expires_at"] = expires_at
        await self.client.hset(key, mapping=mapping)
        await self.client.expire(key, self.ttl)

    async def delete_cached_url(self, short_code: str) -> None:
        await self.client.delete(self._key(short_code))

    async def increment_click(self, short_code: str) -> None:
        key = self._key(short_code)
        await self.client.hincrby(key, "clicks", 1)
        now = datetime.now(timezone.utc).isoformat()
        await self.client.hset(key, "last_clicked_at", now)
```

```python
# app/services/__init__.py
from app.services.url_service import URLService

__all__ = ["URLService"]
```

```python
# app/services/short_code_generator.py
import secrets
import string

BASE62_ALPHABET = string.ascii_letters + string.digits

def generate_code(length: int = 6) -> str:
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))
```

```python
# app/services/url_service.py
"""
Business logic service for URL shortening, redirect, stats, and deletion.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from app.repositories.url_repository import URLRepository
from app.repositories.cache_repository import CacheRepository
from app.services.short_code_generator import generate_code
from app.config import settings
from app.exceptions.handlers import (
    URLNotFoundError,
    URLDeletedError,
    URLExpiredError,
    ShortCodeGenerationError,
)

logger = logging.getLogger(__name__)

class URLService:
    def __init__(self, url_repo: URLRepository, cache_repo: CacheRepository):
        self.url_repo = url_repo
        self.cache_repo = cache_repo

    async def shorten_url(
        self, original_url: str, expires_at: Optional[datetime] = None
    ) -> dict:
        # Generate unique short code with collision check (including soft-deleted)
        max_attempts = 5
        code = None
        for _ in range(max_attempts):
            code = generate_code(settings.short_code_length)
            if not await self.url_repo.exists_by_short_code(code):
                break
        else:
            raise ShortCodeGenerationError(
                "Could not generate a unique short code after multiple attempts."
            )

        record = await self.url_repo.create(
            short_code=code,
            original_url=original_url,
            expires_at=expires_at,
        )

        # Cache the new URL (ignore failures, non-critical)
        try:
            await self.cache_repo.set_cached_url(
                short_code=code,
                original_url=record.original_url,
                created_at=record.created_at.isoformat(),
                expires_at=record.expires_at.isoformat() if record.expires_at else None,
                is_deleted=False,
            )
        except Exception as e:
            logger.warning(f"Failed to cache URL on creation: {e}")

        return {
            "short_code": code,
            "short_url": f"{settings.base_url}/{code}",
            "original_url": record.original_url,
            "created_at": record.created_at,
            "expires_at": record.expires_at,
        }

    async def get_redirect_url(self, short_code: str) -> str:
        # Try cache first, graceful degradation on Redis failure
        cached = None
        try:
            cached = await self.cache_repo.get_cached_url(short_code)
        except Exception as e:
            logger.warning(f"Redis error during redirect cache lookup: {e}")

        if cached:
            if cached.get("is_deleted") == "1":
                raise URLDeletedError()
            expires_at = cached.get("expires_at")
            if expires_at:
                try:
                    exp = datetime.fromisoformat(expires_at)
                    if exp.tzinfo is None:
                        exp = exp.replace(tzinfo=timezone.utc)
                    if datetime.now(timezone.utc) > exp:
                        raise URLExpiredError()
                except ValueError:
                    pass
            # Cache hit: increment click in Redis (ignore failure)
            try:
                await self.cache_repo.increment_click(short_code)
            except Exception as e:
                logger.warning(f"Failed to increment Redis click: {e}")
            return cached["original_url"]

        # Cache miss: query database
        record = await self.url_repo.get_by_short_code(short_code)
        if record is None:
            raise URLNotFoundError()
        if record.is_deleted:
            raise URLDeletedError()
        if record.expires_at and datetime.now(timezone.utc) > record.expires_at:
            raise URLExpiredError()

        # Populate cache (ignore failure)
        try:
            await self.cache_repo.set_cached_url(
                short_code=record.short_code,
                original_url=record.original_url,
                created_at=record.created_at.isoformat(),
                expires_at=record.expires_at.isoformat() if record.expires_at else None,
                is_deleted=False,
            )
        except Exception as e:
            logger.warning(f"Failed to cache URL during redirect: {e}")

        await self.url_repo.update_click_and_last_access(record)
        return record.original_url

    async def get_stats(self, short_code: str) -> dict:
        record = await self.url_repo.get_by_short_code(short_code)
        if record is None:
            raise URLNotFoundError()

        is_active = not record.is_deleted
        if is_active and record.expires_at:
            is_active = datetime.now(timezone.utc) <= record.expires_at

        return {
            "short_code": record.short_code,
            "original_url": record.original_url,
            "created_at": record.created_at,
            "click_count": record.click_count,
            "last_clicked_at": record.last_clicked_at,
            "is_active": is_active,
        }

    async def delete_url(self, short_code: str) -> None:
        record = await self.url_repo.get_by_short_code(short_code)
        if record is None:
            raise URLNotFoundError()

        await self.url_repo.soft_delete(record)
        # Clear cache, ignore errors
        try:
            await self.cache_repo.delete_cached_url(short_code)
        except Exception as e:
            logger.warning(f"Failed to delete cache for {short_code}: {e}")
```

```python
# app/services/sync_service.py
"""
Background service to synchronize click counts from Redis to PostgreSQL.
"""
import asyncio
import logging
from redis.asyncio import Redis
from app.repositories.url_repository import URLRepository
from app.config import settings
from sqlalchemy.ext.asyncio import async_sessionmaker

logger = logging.getLogger(__name__)

ATOMIC_GET_AND_CLEAR_CLICKS = """
local clicks = redis.call('HGET', KEYS[1], 'clicks')
if clicks then
    redis.call('HDEL', KEYS[1], 'clicks')
end
return clicks
"""

class SyncService:
    def __init__(self):
        self._task: asyncio.Task | None = None

    async def sync_clicks(self, redis: Redis, db_session_factory: async_sessionmaker) -> None:
        try:
            updates: dict[str, int] = {}
            async for key in redis.scan_iter(match="url:*"):
                short_code = key.decode().split(":", 1)[1] if isinstance(key, bytes) else key.split(":", 1)[1]
                clicks_bytes = await redis.eval(ATOMIC_GET_AND_CLEAR_CLICKS, 1, key)
                if clicks_bytes:
                    clicks = int(clicks_bytes)
                    if clicks > 0:
                        updates[short_code] = clicks
            if not updates:
                return

            logger.info(f"Syncing click counts for {len(updates)} short codes.")
            async with db_session_factory() as session:
                repo = URLRepository(session)
                for short_code, clicks in updates.items():
                    await repo.update_click_and_last_access_by_short_code(short_code, clicks)
                await session.commit()
        except Exception as e:
            logger.error(f"Error during click sync: {e}", exc_info=True)

    async def start(self, redis: Redis, db_session_factory: async_sessionmaker):
        logger.info("Starting background click sync service.")
        while True:
            await asyncio.sleep(settings.sync_interval_seconds)
            await self.sync_clicks(redis, db_session_factory)
```

```python
# app/routers/__init__.py
# routers package
```

```python
# app/routers/shorten.py
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_async_session
from app.services.url_service import URLService
from app.repositories.url_repository import URLRepository
from app.repositories.cache_repository import CacheRepository
from app.schemas.url import ShortenRequest, ShortenResponse
from app.middleware.rate_limiter import limiter
from app.config import settings
from app.redis_client import get_redis_client
import redis.asyncio as aioredis

router = APIRouter()

@router.post(
    "/",
    response_model=ShortenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Shorten a URL",
    description="Creates a short URL from a long URL. Optionally set expiration.",
)
@limiter.limit(settings.rate_limit_shorten)
async def create_short_url(
    request: Request,
    request_data: ShortenRequest,
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> ShortenResponse:
    url_repo = URLRepository(session)
    cache_repo = CacheRepository(redis)
    service = URLService(url_repo, cache_repo)

    result = await service.shorten_url(
        original_url=str(request_data.url),
        expires_at=request_data.expires_at,
    )
    return ShortenResponse(**result)
```

```python
# app/routers/redirect.py
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_async_session
from app.services.url_service import URLService
from app.repositories.url_repository import URLRepository
from app.repositories.cache_repository import CacheRepository
from app.middleware.rate_limiter import limiter
from app.config import settings
from app.redis_client import get_redis_client
import redis.asyncio as aioredis

router = APIRouter()

@router.get(
    "/{short_code}",
    status_code=status.HTTP_302_FOUND,
    summary="Redirect to original URL",
    description="Redirects using the short code. Returns 404 if not found, 410 if expired.",
    response_class=RedirectResponse,
)
@limiter.limit(settings.rate_limit_redirect)
async def redirect_to_url(
    request: Request,
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_client),
):
    url_repo = URLRepository(session)
    cache_repo = CacheRepository(redis)
    service = URLService(url_repo, cache_repo)

    original_url = await service.get_redirect_url(short_code)
    return RedirectResponse(url=original_url, status_code=302)
```

```python
# app/routers/stats.py
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_async_session
from app.services.url_service import URLService
from app.repositories.url_repository import URLRepository
from app.repositories.cache_repository import CacheRepository
from app.schemas.url import StatsResponse
from app.middleware.rate_limiter import limiter
from app.config import settings
from app.redis_client import get_redis_client
import redis.asyncio as aioredis

router = APIRouter()

@router.get(
    "/{short_code}",
    response_model=StatsResponse,
    summary="Get URL statistics",
    description="Returns click count, creation date, last click, and active status.",
)
@limiter.limit(settings.rate_limit_stats)
async def get_url_stats(
    request: Request,
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_client),
):
    url_repo = URLRepository(session)
    cache_repo = CacheRepository(redis)
    service = URLService(url_repo, cache_repo)
    stats = await service.get_stats(short_code)
    return StatsResponse(**stats)
```

```python
# app/routers/health.py
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_async_session
from app.redis_client import get_redis_client
from app.schemas.common import HealthResponse
from sqlalchemy import text
import redis.asyncio as aioredis

router = APIRouter(tags=["health"])

@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check",
)
async def health_check(
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_client),
) -> HealthResponse:
    db_ok = False
    redis_ok = False
    try:
        await session.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    try:
        await redis.ping()
        redis_ok = True
    except Exception:
        pass

    status_text = "ok" if (db_ok and redis_ok) else "degraded"
    return HealthResponse(
        status=status_text,
        db_connected=db_ok,
        redis_connected=redis_ok,
    )
```

```python
# app/routers/delete.py
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.dependencies import get_async_session
from app.services.url_service import URLService
from app.repositories.url_repository import URLRepository
from app.repositories.cache_repository import CacheRepository
from app.middleware.rate_limiter import limiter
from app.config import settings
from app.redis_client import get_redis_client
import redis.asyncio as aioredis

router = APIRouter()

@router.delete(
    "/{short_code}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a short URL",
    description="Soft-deletes the short URL. Returns 204 if successful, 404 if not found.",
)
@limiter.limit(settings.rate_limit_delete)
async def delete_url(
    request: Request,
    short_code: str,
    session: AsyncSession = Depends(get_async_session),
    redis: aioredis.Redis = Depends(get_redis_client),
):
    url_repo = URLRepository(session)
    cache_repo = CacheRepository(redis)
    service = URLService(url_repo, cache_repo)
    await service.delete_url(short_code)
```

```python
# app/middleware/__init__.py
# middleware package
```

```python
# app/middleware/rate_limiter.py
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.config import settings

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[],
    storage_uri=settings.redis_url,
)
```

```python
# app/utils/__init__.py
# utils package
```

```python
# app/utils/url_validator.py
"""
URL validation utilities, especially SSRF protection.
"""
from urllib.parse import urlparse
import ipaddress
import socket

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain"}

def is_ip_blocked(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return False
    return any(ip in net for net in BLOCKED_IP_NETWORKS)

def validate_url_no_ssrf(url: str) -> None:
    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Missing hostname in URL")
    if hostname.lower() in BLOCKED_HOSTNAMES:
        raise ValueError(f"URL points to forbidden hostname: {hostname}")
    try:
        ip = socket.getaddrinfo(hostname, None)[0][4][0]
    except (socket.gaierror, IndexError):
        return
    if is_ip_blocked(ip):
        raise ValueError(f"URL resolves to a blocked IP address: {ip}")
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        if is_ip_blocked(hostname):
            raise ValueError(f"URL contains a blocked IP address: {hostname}")
```

```python
# app/exceptions/__init__.py
from app.exceptions.handlers import (
    URLNotFoundError,
    URLDeletedError,
    URLExpiredError,
    ShortCodeGenerationError,
    register_exception_handlers,
)

__all__ = [
    "URLNotFoundError",
    "URLDeletedError",
    "URLExpiredError",
    "ShortCodeGenerationError",
    "register_exception_handlers",
]
```

```python
# app/exceptions/handlers.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.schemas.common import ErrorResponse

class URLNotFoundError(Exception):
    pass

class URLDeletedError(Exception):
    pass

class URLExpiredError(Exception):
    pass

class ShortCodeGenerationError(Exception):
    pass

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(URLNotFoundError)
    async def url_not_found_exception_handler(request: Request, exc: URLNotFoundError):
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                detail="Short URL not found.",
                error_code="not_found",
                status_code=404,
            ).model_dump(),
        )

    @app.exception_handler(URLDeletedError)
    async def url_deleted_exception_handler(request: Request, exc: URLDeletedError):
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                detail="Short URL has been deleted.",
                error_code="not_found",
                status_code=404,
            ).model_dump(),
        )

    @app.exception_handler(URLExpiredError)
    async def url_expired_exception_handler(request: Request, exc: URLExpiredError):
        return JSONResponse(
            status_code=410,
            content=ErrorResponse(
                detail="Short URL has expired.",
                error_code="gone",
                status_code=410,
            ).model_dump(),
        )

    @app.exception_handler(ShortCodeGenerationError)
    async def short_code_generation_error_handler(request: Request, exc: ShortCodeGenerationError):
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                detail="Could not generate a unique short code. Try again later.",
                error_code="internal_error",
                status_code=500,
            ).model_dump(),
        )
```

```python
# tests/__init__.py
# tests package
```

```python
# tests/conftest.py
import asyncio
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.database import Base, get_async_session
from app.redis_client import get_redis_client
from app.main import app
from app.config import settings
from app.middleware.rate_limiter import limiter
from slowapi.storage import MemoryStorage

# Override base_url for tests
settings.base_url = "http://test"

TEST_DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/test_urlshortener"

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(test_engine):
    async_session = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

@pytest_asyncio.fixture
async def redis_client():
    import fakeredis.aioredis
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.close()

@pytest.fixture
def override_dependencies(db_session, redis_client):
    async def override_get_db():
        yield db_session
    async def override_get_redis():
        yield redis_client
    app.dependency_overrides[get_async_session] = override_get_db
    app.dependency_overrides[get_redis_client] = override_get_redis
    yield
    app.dependency_overrides.clear()

@pytest.fixture(autouse=True)
def setup_rate_limiter(override_dependencies):
    old_storage = limiter.storage
    limiter.storage = MemoryStorage()
    yield
    limiter.storage = old_storage

@pytest_asyncio.fixture
async def client(override_dependencies):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
```

```python
# tests/test_shorten.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_shorten_url_success(client: AsyncClient):
    long_url = "https://example.com/very/long/path?param=value"
    response = await client.post("/shorten/", json={"url": long_url})
    assert response.status_code == 201
    data = response.json()
    assert "short_code" in data
    assert len(data["short_code"]) == 6
    assert data["original_url"] == long_url
    assert data["short_url"].startswith("http://test/")
    assert data["expires_at"] is None

@pytest.mark.asyncio
async def test_shorten_url_with_expiration(client: AsyncClient):
    response = await client.post("/shorten/", json={
        "url": "https://example.com",
        "expires_at": "2025-12-31T23:59:59Z"
    })
    assert response.status_code == 201
    data = response.json()
    # Pydantic serializes with timezone offset, so we only check the beginning
    assert data["expires_at"].startswith("2025-12-31T23:59:59")

@pytest.mark.asyncio
async def test_shorten_url_invalid_url(client: AsyncClient):
    response = await client.post("/shorten/", json={"url": "not_a_url"})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_shorten_url_ssrf_blocked(client: AsyncClient):
    response = await client.post("/shorten/", json={"url": "http://127.0.0.1/admin"})
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_shorten_url_rate_limiting(client: AsyncClient):
    responses = []
    for _ in range(12):
        resp = await client.post("/shorten/", json={"url": "https://unique.com"})
        responses.append(resp.status_code)
    assert 429 in responses
```

```python
# tests/test_redirect.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_redirect_success(client: AsyncClient):
    create_resp = await client.post("/shorten/", json={"url": "https://example.com/target"})
    assert create_resp.status_code == 201
    short_code = create_resp.json()["short_code"]
    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "https://example.com/target"

@pytest.mark.asyncio
async def test_redirect_not_found(client: AsyncClient):
    resp = await client.get("/nonexistent", follow_redirects=False)
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_redirect_expired(client: AsyncClient):
    resp_create = await client.post("/shorten/", json={
        "url": "https://example.com",
        "expires_at": "2020-01-01T00:00:00Z"
    })
    short_code = resp_create.json()["short_code"]
    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 410

@pytest.mark.asyncio
async def test_redirect_after_delete(client: AsyncClient):
    resp_create = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = resp_create.json()["short_code"]
    del_resp = await client.delete(f"/{short_code}")
    assert del_resp.status_code == 204
    resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert resp.status_code == 404
```

```python
# tests/test_stats.py
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
from app.repositories.url_repository import URLRepository

@pytest.mark.asyncio
async def test_stats_success(client: AsyncClient, test_engine, redis_client):
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    # Simulate a few clicks
    for _ in range(3):
        await client.get(f"/{short_code}", follow_redirects=False)

    # Sync Redis clicks to DB so the stats reflect them
    async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        repo = URLRepository(session)
        clicks_bytes = await redis_client.hget(f"url:{short_code}", "clicks")
        if clicks_bytes:
            clicks = int(clicks_bytes)
            await repo.update_click_and_last_access_by_short_code(short_code, clicks)
            await session.commit()

    resp = await client.get(f"/stats/{short_code}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["short_code"] == short_code
    assert data["click_count"] == 3
    assert data["is_active"] == True
    assert data["last_clicked_at"] is not None

@pytest.mark.asyncio
async def test_stats_not_found(client: AsyncClient):
    resp = await client.get("/stats/nonexistent")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_stats_deleted(client: AsyncClient):
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    await client.delete(f"/{short_code}")
    resp = await client.get(f"/stats/{short_code}")
    assert resp.status_code == 404
```

```python
# tests/test_delete.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_delete_success(client: AsyncClient):
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    resp = await client.delete(f"/{short_code}")
    assert resp.status_code == 204
    get_resp = await client.get(f"/{short_code}", follow_redirects=False)
    assert get_resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_nonexistent(client: AsyncClient):
    resp = await client.delete("/nonexistent")
    assert resp.status_code == 404

@pytest.mark.asyncio
async def test_delete_twice(client: AsyncClient):
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    await client.delete(f"/{short_code}")
    resp = await client.delete(f"/{short_code}")
    assert resp.status_code == 404
```

```python
# tests/test_rate_limit.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_rate_limit_redirect(client: AsyncClient):
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    statuses = []
    for _ in range(105):
        resp = await client.get(f"/{short_code}", follow_redirects=False)
        statuses.append(resp.status_code)
    assert 429 in statuses

@pytest.mark.asyncio
async def test_rate_limit_stats(client: AsyncClient):
    create_resp = await client.post("/shorten/", json={"url": "https://example.com"})
    short_code = create_resp.json()["short_code"]
    for _ in range(35):
        await client.get(f"/stats/{short_code}")
    resp = await client.get(f"/stats/{short_code}")
    assert resp.status_code == 429
```

```python
# tests/test_validation.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_valid_url_accepted(client: AsyncClient):
    valid_urls = [
        "https://example.com",
        "http://test.co.uk/path?q=1",
        "https://sub.domain.com:8080/",
    ]
    for url in valid_urls:
        resp = await client.post("/shorten/", json={"url": url})
        assert resp.status_code == 201, f"Failed for {url}"

@pytest.mark.asyncio
async def test_invalid_url_rejected(client: AsyncClient):
    invalid_urls = [
        "not_a_url",
        "ftp://invalid-scheme.com",
        "htp://example.com",
        "localhost",
    ]
    for url in invalid_urls:
        resp = await client.post("/shorten/", json={"url": url})
        assert resp.status_code == 422, f"Should fail for {url}"

@pytest.mark.asyncio
async def test_ssrf_localhost_blocked(client: AsyncClient):
    blocked = [
        "http://localhost/admin",
        "http://127.0.0.1:9000",
        "http://10.0.0.1/api",
        "http://[::1]/",
    ]
    for url in blocked:
        resp = await client.post("/shorten/", json={"url": url})
        assert resp.status_code == 422, f"Should block {url}"
```

```python
# tests/test_health.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_health_ok(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["db_connected"] is True
    assert data["redis_connected"] is True
```

```yaml
# docker-compose.yml
version: '3.9'

services:
  db:
    image: postgres:16-alpine
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
      - POSTGRES_DB=urlshortener
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5

  app:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./app:/app
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --log-level info"

volumes:
  pgdata:
```

```dockerfile
# Dockerfile
FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```text
# requirements.txt
fastapi>=0.115,<1.0
uvicorn[standard]>=0.30,<0.35
sqlalchemy[asyncio]>=2.0,<3.0
asyncpg>=0.29,<1.0
redis>=5.0,<6.0
pydantic>=2.0,<3.0
pydantic-settings>=2.0,<3.0
alembic>=1.13,<2.0
slowapi>=0.1.9,<1.0
httpcore>=1.0,<2.0
httpx>=0.27,<1.0
python-dotenv>=1.0,<2.0
email-validator>=2.0,<3.0

pytest>=8.0,<9.0
pytest-asyncio>=0.24,<1.0
pytest-cov>=5.0,<6.0
fakeredis[json]>=2.20,<3.0
aiosqlite>=0.20,<1.0
```

```text
# .env.example
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener
REDIS_URL=redis://localhost:6379/0
BASE_URL=http://localhost:8000
SHORT_CODE_LENGTH=6
CACHE_TTL_SECONDS=3600
RATE_LIMIT_SHORTEN=10/minute
RATE_LIMIT_REDIRECT=100/minute
RATE_LIMIT_STATS=30/minute
RATE_LIMIT_DELETE=10/minute
```

```ini
# alembic.ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://postgres:postgres@localhost:5432/urlshortener

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
# alembic/env.py
import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from app.models import Base
from app.config import settings

config = context.config
if not config.get_main_option("sqlalchemy.url"):
    config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
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
    asyncio.run(run_async_migrations())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

```python
# alembic/script.py.mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

revision: str = ${repr(up_revision)}
down_revision: Union[str, None] = ${repr(down_revision)}
branch_labels: Union[str, Sequence[str], None] = ${repr(branch_labels)}
depends_on: Union[str, Sequence[str], None] = ${repr(depends_on)}

def upgrade() -> None:
    ${upgrades if upgrades else "pass"}

def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
```

```python
# alembic/versions/001_initial.py
"""Initial migration: create urls table

Revision ID: 001_initial
Revises: None
Create Date: 2025-01-20 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.create_table(
        'urls',
        sa.Column('id', sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column('short_code', sa.String(length=6), nullable=False),
        sa.Column('original_url', sa.Text(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column('click_count', sa.BigInteger(), server_default=sa.text("0"), nullable=False),
        sa.Column('last_clicked_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('short_code', name='idx_urls_short_code'),
    )
    op.create_index('idx_urls_created_at', 'urls', ['created_at'])
    op.create_index('idx_urls_expires_at', 'urls', ['expires_at'], postgresql_where=sa.text('expires_at IS NOT NULL'))

def downgrade() -> None:
    op.drop_index('idx_urls_expires_at', table_name='urls')
    op.drop_index('idx_urls_created_at', table_name='urls')
    op.drop_table('urls')
```

```python
# README.md excluded as not part of code, but present – omitted for brevity, but would be included in real output. This is not required.
```

---

**Исправления:**

1. **app/dependencies.py**: Добавлен импорт `get_async_session` из `app.database` — устраняет `ImportError`, критический для запуска.
2. **app/routers/shorten.py**: Добавлен параметр `request: Request` в сигнатуру `create_short_url` — обязательное требование slowapi, иначе ошибка при вызове.
3. **app/main.py**: В `lifespan` запущена фоновая задача `SyncService.start`, а при завершении выполняется её отмена и закрытие Redis — реализует периодическую синхронизацию кликов, требуемую архитектурой.
4. **app/redis_client.py**: Создан глобальный экземпляр `redis_client` через `Redis.from_url`; зависимость теперь возвращает его, а не создаёт пул на каждом запросе — устраняет неэффективное использование соединений.
5. **app/repositories/url_repository.py**: Добавлен метод `exists_by_short_code` для проверки наличия кода без учёта `is_deleted` — предотвращает коллизии с мягко удалёнными записями при генерации нового short_code.
6. **app/services/url_service.py**: Обёрнуты все вызовы Redis в `try/except` с логированием — обеспечивает graceful degradation при сбоях кэша; в цикле генерации кода используется `exists_by_short_code` вместо `get_by_short_code`.
7. **app/services/sync_service.py**: Для атомарного получения и удаления кликов из Redis используется Lua-скрипт (`EVAL`) — устраняет race condition между `HGET` и `HDEL`.
8. **tests/conftest.py**: Установлено `settings.base_url = "http://test"` — тесты теперь используют правильный базовый URL.
9. **tests/test_shorten.py**: Проверка `expires_at` заменена на `startswith` — адаптируется к сериализации с timezone offset.
10. **tests/test_stats.py**: После имитации кликов выполняется ручная синхронизация Redis->DB через `URLRepository` и `redis_client` — тест корректно проверяет счётчик.