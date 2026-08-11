"""
Service for aggregating click statistics.
"""
import logging
from typing import Optional

import aiosqlite

from src.repositories.url_repository import UrlRepository
from src.repositories.click_repository import ClickRepository

logger = logging.getLogger(__name__)


class StatsService:
    """Provides statistics for a short URL."""

    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn
        self.url_repo = UrlRepository()
        self.click_repo = ClickRepository()

    async def get_stats(self, code: str) -> Optional[dict]:
        """
        Retrieve statistics for a given short code.
        Returns a dict with code, original_url, created_at, total_clicks, recent_clicks,
        or None if code not found.
        """
        url_record = await self.url_repo.get_url_by_code(self.conn, code)
        if url_record is None:
            return None
        url_id = url_record["id"]
        total_clicks = await self.click_repo.count_clicks(self.conn, url_id)
        recent_clicks = await self.click_repo.get_recent_clicks(self.conn, url_id, limit=10)
        return {
            "code": url_record["code"],
            "original_url": url_record["original_url"],
            "created_at": url_record["created_at"],
            "total_clicks": total_clicks,
            "recent_clicks": recent_clicks,
        }
