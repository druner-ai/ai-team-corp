"""
    GET /stats/{id} endpoint.
"""
import re
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
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
    redis: Optional[aioredis.Redis] = Depends(get_redis),
):
    if not ID_PATTERN.match(short_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")
    return await get_stats(db, redis, short_id)