from pydantic import BaseModel, AnyHttpUrl, field_validator


class ShortenRequest(BaseModel):
    url: AnyHttpUrl

    @field_validator("url")
    @classmethod
    def check_length(cls, v):
        url_str = str(v)
        if len(url_str) > 2048:
            raise ValueError("URL too long")
        return v


class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str


class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    clicks: int
    created_at: str
