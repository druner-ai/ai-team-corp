"""
Pydantic schemas for shorten endpoints.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, HttpUrl, Field


class ShortenRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048, description="Original URL to shorten")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date in ISO format")


class ShortenResponse(BaseModel):
    short_id: str
    short_url: str
    original_url: str
    created_at: datetime

    class Config:
        from_attributes = True