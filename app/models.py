from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class URLCreate(BaseModel):
    url: HttpUrl


class URLResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str

    class Config:
        from_attributes = True


class URLStats(BaseModel):
    short_code: str
    original_url: str
    created_at: Optional[datetime] = None
    clicks: int

    class Config:
        from_attributes = True
