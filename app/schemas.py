"""
Pydantic schemas for request/response validation.
"""

from datetime import datetime

from pydantic import BaseModel, HttpUrl


class URLCreateRequest(BaseModel):
    url: HttpUrl


class URLCreateResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


class URLStatsResponse(BaseModel):
    short_code: str
    original_url: str
    access_count: int
    created_at: datetime
