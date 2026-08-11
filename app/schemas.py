from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class ShortenRequest(BaseModel):
    url: HttpUrl


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


class RefererStat(BaseModel):
    referer: str
    count: int


class UserAgentStat(BaseModel):
    user_agent: str
    count: int


class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    click_count: int
    last_click: Optional[datetime] = None
    top_referers: list[RefererStat]
    top_user_agents: list[UserAgentStat]
