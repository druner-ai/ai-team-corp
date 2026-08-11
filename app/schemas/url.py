"""Pydantic models for request/response validation."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl

from app.config import settings


class ShortenRequest(BaseModel):
    """Request body for creating a short link."""

    url: HttpUrl = Field(
        ...,
        max_length=settings.max_url_length,
        description="Original URL to shorten (must start with http:// or https://)",
    )


class ShortenResponse(BaseModel):
    """Response after successful short link creation."""

    short_code: str
    short_url: str
    original_url: str


class StatsResponse(BaseModel):
    """Statistics for a short link."""

    short_code: str
    original_url: str
    clicks: int
    created_at: datetime
    last_visited_at: Optional[datetime] = None
