"""
    GET /{id} endpoint.
"""
import re
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import redis.asyncio as aioredis

from src.dependencies import get_db, get_redis
from src.services.url_shortener import get_url_and_increment

router = APIRouter()
ID_PATTERN = re.compile(r"^[A-Za-z0-9]{7}$")

@router.get("/{short_id}", response_class=RedirectResponse)
async def redirect_to_original(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Optional[aioredis.Redis] = Depends(get_redis),
):
    if not ID_PATTERN.match(short_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")
    original_url = await get_url_and_increment(db, redis, short_id)
    return RedirectResponse(url=original_url, status_code=301)