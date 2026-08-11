from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional


class URLCreate(BaseModel):
    url: HttpUrl


class URLInfo(BaseModel):
    short_code: str
    original_url: str
    short_url: str
    created_at: Optional[datetime]
    last_visited_at: Optional[datetime]
    visits: int

    model_config = {"from_attributes": True}


class URLStats(URLInfo):
    pass
