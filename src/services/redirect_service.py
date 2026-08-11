"""
Service for handling redirects and recording clicks.
"""
import logging
from typing import Optional

import aiosqlite

from src.repositories.url_repository import UrlRepository
from src.repositories.click_repository import ClickRepository

logger = logging.getLogger(__name__)


class RedirectService:
    """Resolves short codes to original URLs and logs clicks."""

    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn
        self.url_repo = UrlRepository()
        self.click_repo = ClickRepository()

    async def get_original_url_and_log(
        self,
        code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[str]:
        """
        Look up the original URL by code, record a click, and return the URL.
        Returns None if code not found.
        """
        url_record = await self.url_repo.get_url_by_code(self.conn, code)
        if url_record is None:
            return None
        # Record click asynchronously (fire-and-forget could be used, but we do it synchronously for MVP)
        await self.click_repo.insert_click(
            self.conn,
            url_record["id"],
            ip_address=ip_address,
            user_agent=user_agent,
        )
        return url_record["original_url"]
