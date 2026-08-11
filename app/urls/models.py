from pydantic import BaseModel, HttpUrl
from typing import Optional


class URLCreate(BaseModel):
    url: HttpUrl
    custom_code: Optional[str] = None
    expires_in_days: Optional[int] = None


class URLResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    created_at: str
    expires_at: Optional[str] = None


class URLStats(BaseModel):
    short_code: str
    original_url: str
    created_at: str
    clicks: int
    last_accessed: Optional[str] = None
