"""
Pydantic schemas for request/response validation.
"""
from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class URLCreate(BaseModel):
    url: HttpUrl
    custom_slug: Optional[str] = None


class URLResponse(BaseModel):
    slug: str
    original_url: str
    short_url: str
    created_at: datetime


class ClickStats(BaseModel):
    slug: str
    original_url: str
    created_at: datetime
    total_clicks: int
    clicks: Optional[list[dict]] = None
