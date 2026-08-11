from pydantic import BaseModel, Field, validator
from typing import Optional
import re


class URLCreate(BaseModel):
    url: str
    custom_code: Optional[str] = Field(None, min_length=3, max_length=20)
    expires_at: Optional[str] = None

    @validator('url')
    def validate_url_scheme(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

    @validator('custom_code')
    def validate_custom_code(cls, v):
        if v is not None:
            if not re.match(r'^[a-zA-Z0-9_-]+$', v):
                raise ValueError('Custom code must contain only alphanumeric characters, underscore, or hyphen')
        return v


class URLResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    created_at: str
    expires_at: Optional[str] = None


class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: str
    expires_at: Optional[str] = None
    is_active: bool
    total_clicks: int
    last_click_at: Optional[str] = None
    clicks_today: int
    clicks_last_7_days: int
