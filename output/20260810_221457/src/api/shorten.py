"""
    POST /shorten endpoint.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import redis.asyncio as aioredis

from src.dependencies import get_db, get_redis
from src.schemas.shorten import ShortenRequest, ShortenResponse
from src.services.url_shortener import create_short_url

router = APIRouter()

@router.post("/shorten", response_model=ShortenResponse, status_code=status.HTTP_201_CREATED)
async def shorten_url(
    request: ShortenRequest,
    db: AsyncSession = Depends(get_db),
    redis: Optional[aioredis.Redis] = Depends(get_redis),
):
    return await create_short_url(db, redis, request.url, request.expires_at)