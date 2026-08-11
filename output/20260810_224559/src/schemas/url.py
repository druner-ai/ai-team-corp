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