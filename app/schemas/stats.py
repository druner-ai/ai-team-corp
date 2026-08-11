from pydantic import BaseModel


class ClickInfo(BaseModel):
    clicked_at: str
    ip_address: str | None
    user_agent: str | None


class StatsResponse(BaseModel):
    slug: str
    original_url: str
    created_at: str
    total_clicks: int
    recent_clicks: list[ClickInfo]
