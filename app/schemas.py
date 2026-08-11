from pydantic import BaseModel, HttpUrl


class URLCreate(BaseModel):
    url: HttpUrl


class URLInfo(BaseModel):
    short_code: str
    short_url: str


class URLStats(BaseModel):
    url: str
    clicks: int
    created_at: str
