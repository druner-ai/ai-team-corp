from pydantic import BaseModel, HttpUrl, Field
from datetime import datetime
from typing import Optional


class UrlCreateRequest(BaseModel):
    url: HttpUrl


class UrlCreateResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


class UrlRecord(BaseModel):
    id: int
    short_code: str
    original_url: str
    created_at: str
    expires_at: Optional[str] = None
    is_active: int


class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    clicks_total: int
    created_at: str
    last_click_at: Optional[str] = None
