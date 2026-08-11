import secrets
import string
from typing import Optional
from app.urls.repository import (
    create_url, get_url_by_code, deactivate_url, url_exists, record_click, get_click_stats
)
from app.urls.schemas import URLResponse, StatsResponse
from fastapi import Request


def generate_short_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def create_short_url(db, url: str, custom_code: Optional[str] = None, expires_at: Optional[str] = None, request: Request = None) -> URLResponse:
    if custom_code:
        if url_exists(db, custom_code):
            raise ValueError("Custom code already exists")
        short_code = custom_code
    else:
        while True:
            short_code = generate_short_code()
            if not url_exists(db, short_code):
                break

    url_id = create_url(db, short_code, url, expires_at)
    short_url = str(request.base_url) + short_code if request else f"http://localhost:8000/{short_code}"
    url_data = get_url_by_code(db, short_code)
    return URLResponse(
        short_code=short_code,
        short_url=short_url,
        original_url=url,
        created_at=url_data["created_at"],
        expires_at=expires_at
    )


def delete_short_url(db, short_code: str) -> bool:
    return deactivate_url(db, short_code)


def get_redirect_url(db, short_code: str, request: Request = None) -> Optional[str]:
    url_data = get_url_by_code(db, short_code)
    if not url_data or not url_data["is_active"]:
        return None
    if url_data["expires_at"]:
        from datetime import datetime
        expires = datetime.fromisoformat(url_data["expires_at"].replace("Z", "+00:00"))
        if expires < datetime.utcnow():
            return "expired"
    ip = request.client.host if request else None
    ua = request.headers.get("user-agent") if request else None
    record_click(db, url_data["id"], ip, ua)
    return url_data["original_url"]


def get_stats(db, short_code: str) -> Optional[StatsResponse]:
    url_data = get_url_by_code(db, short_code)
    if not url_data or not url_data["is_active"]:
        return None
    stats = get_click_stats(db, url_data["id"])
    return StatsResponse(
        short_code=url_data["short_code"],
        original_url=url_data["original_url"],
        created_at=url_data["created_at"],
        expires_at=url_data["expires_at"],
        is_active=bool(url_data["is_active"]),
        total_clicks=stats["total_clicks"],
        last_click_at=stats["last_click_at"],
        clicks_today=stats["clicks_today"],
        clicks_last_7_days=stats["clicks_last_7_days"]
    )
