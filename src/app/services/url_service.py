from datetime import datetime, timezone
from typing import Optional

import aiosqlite

from ..config import settings
from ..repositories import urls_repo
from ..utils.codegen import generate_code
from ..utils.url_utils import is_valid_url, normalize_url


async def create_short_url(
    conn: aiosqlite.Connection,
    url: str,
    custom_code: Optional[str] = None,
    expires_at: Optional[datetime] = None,
    reuse: bool = True,
) -> dict:
    """Create a short URL or return an existing one if reuse is enabled."""
    if not is_valid_url(url):
        raise ValueError("Invalid URL")

    normalized = normalize_url(url)
    now = datetime.now(timezone.utc).isoformat()

    # Duplicate check (when no custom code requested)
    if reuse and not custom_code:
        existing = await urls_repo.get_by_url(conn, normalized)
        if existing:
            return {
                "code": existing["code"],
                "short_url": f"{settings.BASE_URL}/{existing['code']}",
                "original_url": existing["original_url"],
                "created_at": existing["created_at"],
                "expires_at": existing["expires_at"],
            }

    code = custom_code
    if code is None:
        # Auto-generate code (up to 5 attempts to avoid collision)
        for _ in range(5):
            candidate = generate_code(settings.CODE_LENGTH)
            if await urls_repo.get_by_code(conn, candidate) is None:
                code = candidate
                break
        if code is None:
            raise RuntimeError("Failed to generate unique short code after 5 attempts")
    else:
        # Validate custom code (already validated by Pydantic, but check uniqueness)
        if await urls_repo.get_by_code(conn, code) is not None:
            raise ValueError(f"Custom code '{code}' already in use")

    expires_iso = expires_at.isoformat() if expires_at else None
    await urls_repo.insert_url(conn, code, normalized, now, expires_iso)
    return {
        "code": code,
        "short_url": f"{settings.BASE_URL}/{code}",
        "original_url": normalized,
        "created_at": now,
        "expires_at": expires_iso,
    }
