"""
    URL shortening business logic.
"""
import json
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import redis.asyncio as aioredis

from src.models.url_mapping import UrlMapping
from src.services.id_generator import generate_unique_id
from src.config import settings
from src.schemas.shorten import ShortenResponse

logger = logging.getLogger(__name__)

async def create_short_url(
    db: AsyncSession,
    redis: Optional[aioredis.Redis],
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
    # Cache in Redis
    if redis:
        # Store URL and expiration timestamp as JSON
        cache_value = json.dumps({
            "url": url,
            "expires_at": expires_at.isoformat() if expires_at else None,
        })
        await redis.set(f"url:{short_id}", cache_value, ex=settings.CACHE_TTL_SECONDS)
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
    redis: Optional[aioredis.Redis],
    short_id: str,
) -> str:
    # 1. Try cache
    if redis:
        cached = await redis.get(f"url:{short_id}")
        if cached:
            try:
                data = json.loads(cached)
                redis_url = data.get("url")
                redis_expires = data.get("expires_at")
                if redis_expires:
                    expires_at = datetime.fromisoformat(redis_expires)
                    if expires_at <= datetime.now(timezone.utc):
                        # Expired, invalidate cache and raise 410
                        await redis.delete(f"url:{short_id}", f"stats:{short_id}")
                        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short URL expired")
                # Valid cache hit, increment counter
                await redis.incr(f"stats:{short_id}")
                return redis_url
            except (json.JSONDecodeError, ValueError):
                # Corrupted cache, delete and fall through to DB
                await redis.delete(f"url:{short_id}")

    # 2. Cache miss or redis unavailable: query DB
    stmt = select(UrlMapping).where(UrlMapping.id == short_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None or entry.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
    if entry.expires_at and entry.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Short URL expired")
    # Cache if redis available
    if redis:
        cache_value = json.dumps({
            "url": entry.original_url,
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
        })
        await redis.set(f"url:{short_id}", cache_value, ex=settings.CACHE_TTL_SECONDS)
        await redis.incr(f"stats:{short_id}")
    return entry.original_url

async def delete_short_url(
    db: AsyncSession,
    redis: Optional[aioredis.Redis],
    short_id: str,
):
    stmt = select(UrlMapping).where(UrlMapping.id == short_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None or entry.is_deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
    entry.is_deleted = True
    db.add(entry)
    if redis:
        await redis.delete(f"url:{short_id}", f"stats:{short_id}")