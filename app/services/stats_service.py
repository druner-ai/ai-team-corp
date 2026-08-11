from typing import Optional, Dict, Any
import aiosqlite

from app.repositories.url_repository import get_stats_by_code


async def get_stats(
    db: aiosqlite.Connection, code: str
) -> Optional[Dict[str, Any]]:
    """
    Retrieve statistics for a short URL.
    Returns None if the code does not exist.
    """
    record = await get_stats_by_code(db, code)
    if record:
        return {
            "code": record["code"],
            "original_url": record["original_url"],
            "clicks": record["clicks"],
            "created_at": record["created_at"],
            "last_clicked_at": record.get("last_clicked_at"),
        }
    return None
