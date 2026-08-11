"""
Pydantic schemas for URL-related API requests and responses.
"""

import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, HttpUrl

from app.utils.url_validator import validate_and_normalize_url


class URLCreate(BaseModel):
    """Schema for creating a new short URL."""

    original_url: str = Field(..., description="Original URL to shorten")
    custom_code: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=16,
        pattern=r"^[a-zA-Z0-9_-]+$",
        description="Custom short code (3-16 alphanumeric chars, hyphens, underscores)",
    )
    expires_at: Optional[datetime] = Field(
        default=None,
        description="Expiration date in ISO 8601 format",
    )

    @field_validator("original_url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate and normalize the original URL."""
        return validate_and_normalize_url(v)


class URLResponse(BaseModel):
    """Schema for short URL creation response."""

    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None


class URLInfo(BaseModel):
    """Schema for URL information response."""

    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    clicks_count: int
    last_click_at: Optional[datetime] = None
