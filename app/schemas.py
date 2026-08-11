from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional


class ShortenRequest(BaseModel):
    url: HttpUrl


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str


class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    clicks: int
    last_clicked_at: Optional[datetime] = None
    top_referers: list[tuple[str, int]] = []
    top_user_agents: list[tuple[str, int]] = []
