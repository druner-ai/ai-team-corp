"""
Pydantic schemas for URL shortening request/response.
"""
from pydantic import BaseModel, HttpUrl, field_validator


class ShortenRequest(BaseModel):
    """Request body for creating a short URL."""
    url: HttpUrl  # Pydantic's HttpUrl validates http/https scheme and domain structure

    @field_validator("url")
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        """Additional validation if needed – here we only allow http and https (ensured by HttpUrl)."""
        # HttpUrl already restricts to http/https. Uncomment for extra SSRF checks.
        # if v.host and is_private_ip(v.host):
        #     raise ValueError("URL points to private network")
        return v


class ShortenResponse(BaseModel):
    """Response after successful URL shortening."""
    id: str
    short_url: str
    original_url: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "aB3x9Kq",
                "short_url": "http://localhost:8000/aB3x9Kq",
                "original_url": "https://example.com/very/long/path?query=1",
            }
        }
    }