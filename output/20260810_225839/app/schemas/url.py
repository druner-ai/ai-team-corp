"""
Pydantic models for URL shortening requests and responses.
"""
from pydantic import BaseModel, HttpUrl, field_serializer, field_validator
from datetime import datetime
from typing import Optional
from app.utils.url_validator import validate_url_no_ssrf


class ShortenRequest(BaseModel):
    url: HttpUrl
    expires_at: Optional[datetime] = None

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: HttpUrl) -> HttpUrl:
        """Validate URL and protect against SSRF."""
        validate_url_no_ssrf(str(v))
        return v


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str
    created_at: datetime
    expires_at: Optional[datetime] = None

    @field_serializer("created_at")
    def serialize_datetime(self, dt: datetime) -> str:
        return dt.isoformat()

    @field_serializer("expires_at")
    def serialize_expires_at(self, dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None


class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    created_at: datetime
    click_count: int
    last_clicked_at: Optional[datetime]
    is_active: bool

    @field_serializer("created_at")
    def serialize_created(self, dt: datetime) -> str:
        return dt.isoformat()

    @field_serializer("last_clicked_at")
    def serialize_last_clicked(self, dt: Optional[datetime]) -> Optional[str]:
        return dt.isoformat() if dt else None