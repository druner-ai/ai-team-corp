"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, AnyUrl, Field
from typing import Optional


class UrlCreateRequest(BaseModel):
    """Request schema for creating a short URL."""
    original_url: AnyUrl


class UrlCreateResponse(BaseModel):
    """Response schema after successful short URL creation."""
    short_code: str
    original_url: str
    short_url: str


class UrlStatsResponse(BaseModel):
    """Response schema for URL statistics."""
    short_code: str
    original_url: str
    created_at: str
    clicks_count: int
