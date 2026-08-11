from pydantic import BaseModel, HttpUrl
from datetime import datetime


class URLCreate(BaseModel):
    url: str


class URLInfo(BaseModel):
    short_code: str
    short_url: str


class URLStats(BaseModel):
    original_url: str
    created_at: datetime
    access_count: int
