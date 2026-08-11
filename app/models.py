from pydantic import BaseModel, HttpUrl

class ShortenRequest(BaseModel):
    url: str  # Using str to allow any format, tests send plain string

class ShortenResponse(BaseModel):
    short_code: str
    short_url: str
    original_url: str

class StatsResponse(BaseModel):
    short_code: str
    original_url: str
    clicks: int
    created_at: str
