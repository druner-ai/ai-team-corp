"""
    Statistics service: syncs Redis counter to DB and returns aggregated stats.
"""
import logging
from datetime import datetime, timezone
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import redis.asyncio as aioredis

from src.models.url_mapping import UrlMapping
from src.schemas.stats import StatsResponse

logger = logging.getLogger(__name__)

async def sync_click_count(db: AsyncSession, redis: Optional[aioredis.Redis], short_id: str):
    if not redis:
        return
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
    redis: Optional[aioredis.Redis],
    short_id: str,
) -> StatsResponse:
    await sync_click_count(db, redis, short_id)
    stmt = select(UrlMapping).where(UrlMapping.id == short_id)
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Short URL not found")
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