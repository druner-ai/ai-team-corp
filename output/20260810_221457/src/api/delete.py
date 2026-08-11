"""
    DELETE /{id} endpoint.
"""
import re
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import redis.asyncio as aioredis

from src.dependencies import get_db, get_redis
from src.services.url_shortener import delete_short_url

router = APIRouter()
ID_PATTERN = re.compile(r"^[A-Za-z0-9]{7}$")

@router.delete("/{short_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_url(
    short_id: str,
    db: AsyncSession = Depends(get_db),
    redis: Optional[aioredis.Redis] = Depends(get_redis),
):
    if not ID_PATTERN.match(short_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")
    await delete_short_url(db, redis, short_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)