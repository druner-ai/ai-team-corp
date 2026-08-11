"""
    Schemas for /shorten endpoint.
"""
from datetime import datetime
from pydantic import BaseModel, field_validator

class ShortenRequest(BaseModel):
    url: str
    expires_at: datetime | None = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        from src.utils.url_validator import validate_url
        return validate_url(v)

class ShortenResponse(BaseModel):
    short_id: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: datetime | None = None