"""
Schemas for the URL shortening endpoint.
"""

from pydantic import BaseModel, Field, field_validator
from app.core.security import validate_url


class ShortenRequest(BaseModel):
    """
    Request schema for POST /shorten endpoint.

    Attributes:
        url: The long URL to shorten. Must be valid http/https URL.
    """

    url: str = Field(
        ...,
        description="The long URL to shorten",
        max_length=2048,
        examples=["https://example.com/very/long/path?query=1"],
    )

    @field_validator("url")
    @classmethod
    def validate_url_field(cls, v: str) -> str:
        """
        Validate the URL field using security module.

        Args:
            v: The URL string to validate.

        Returns:
            Validated URL string.

        Raises:
            InvalidURLException: If URL is invalid.
        """
        return validate_url(v)


class ShortenResponse(BaseModel):
    """
    Response schema for POST /shorten endpoint.

    Attributes:
        short_code: The generated short code.
        short_url: The full short URL.
        original_url: The original long URL.
    """

    short_code: str = Field(..., description="The generated short code")
    short_url: str = Field(..., description="The full short URL")
    original_url: str = Field(..., description="The original long URL")

    model_config = {
        "json_schema_extra": {
            "example": {
                "short_code": "aB3x9Q",
                "short_url": "http://localhost:8000/aB3x9Q",
                "original_url": "https://example.com/very/long/path?query=1",
            }
        }
    }