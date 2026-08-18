from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class URLCreate(BaseModel):
    url: HttpUrl
    custom_code: Optional[str] = None
    expires_at: Optional[datetime] = None

class URLResponse(BaseModel):
    short_code: str
    url: str
    short_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    clicks: int

class URLStats(BaseModel):
    url: str
    short_code: str
    created_at: datetime
    expires_at: Optional[datetime] = None
    clicks: int
