from pydantic import BaseModel, Field, HttpUrl


class CreateUrlRequest(BaseModel):
    original_url: str
    custom_slug: str | None = Field(None, max_length=100, min_length=1)


class UrlResponse(BaseModel):
    slug: str
    short_url: str
    original_url: str
    created_at: str
