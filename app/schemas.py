from pydantic import BaseModel, HttpUrl

class URLCreate(BaseModel):
    url: HttpUrl

class URLResponse(BaseModel):
    short_url: str
    short_code: str

class URLStats(BaseModel):
    original_url: str
    short_code: str
    visit_count: int
    created_at: str
    last_visited_at: str | None

    class Config:
        from_attributes = True
