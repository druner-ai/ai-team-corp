from pydantic import BaseModel, HttpUrl, field_validator
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class LinkCreate(BaseModel):
    url: HttpUrl
    custom_slug: Optional[str] = None

    @field_validator('url')
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl):
        # HttpUrl already ensures http/https, but we double-check
        if v.scheme not in ('http', 'https'):
            logger.warning(f"Invalid URL scheme: {v.scheme}")
            raise ValueError('URL must use http or https scheme')
        return v


class LinkResponse(BaseModel):
    slug: str
    short_url: str
    original_url: str
    created_at: str  # ISO 8601

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str):
        if not v:
            raise ValueError('Slug cannot be empty')
        return v


class StatsResponse(BaseModel):
    slug: str
    original_url: str
    created_at: str
    clicks_count: int
    last_click_at: Optional[str] = None
    last_click_ip: Optional[str] = None
    last_click_user_agent: Optional[str] = None

    @field_validator('clicks_count')
    @classmethod
    def validate_clicks_count(cls, v: int):
        if v < 0:
            raise ValueError('Clicks count cannot be negative')
        return v


class HealthResponse(BaseModel):
    status: str = "ok"

    @field_validator('status')
    @classmethod
    def validate_status(cls, v: str):
        if v != "ok":
            raise ValueError('Status must be "ok"')
        return v
