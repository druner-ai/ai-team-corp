import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, field_validator


class ShortenRequest(BaseModel):
    url: str
    custom_code: Optional[str] = None
    expires_at: Optional[datetime] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        return v

    @field_validator("custom_code")
    @classmethod
    def validate_custom_code(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.fullmatch(r"[a-zA-Z0-9_-]{4,16}", v):
                raise ValueError(
                    "Custom code must be 4-16 alphanumeric characters, underscores, or hyphens"
                )
        return v


class ShortenResponse(BaseModel):
    code: str
    short_url: str
    original_url: str
    created_at: str
    expires_at: Optional[str] = None


class RefererCount(BaseModel):
    referer: Optional[str]
    count: int


class UserAgentCount(BaseModel):
    user_agent: Optional[str]
    count: int


class StatsResponse(BaseModel):
    code: str
    original_url: str
    created_at: str
    total_clicks: int
    last_click_at: Optional[str]
    top_referers: list[RefererCount]
    top_user_agents: list[UserAgentCount]
