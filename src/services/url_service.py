"""
Service layer for URL shortening business logic.
"""
import logging

import aiosqlite
from fastapi import HTTPException

from src.repositories.url_repository import UrlRepository
from src.utils.code_generator import generate_code
from src.config import settings

logger = logging.getLogger(__name__)


class UrlService:
    """Handles creation of short URLs."""

    def __init__(self, conn: aiosqlite.Connection):
        self.conn = conn
        self.repo = UrlRepository()

    async def create_short_url(self, original_url: str) -> dict:
        """
        Generate a unique short code and persist the URL.
        Returns a dict with code, short_url, original_url.
        """
        max_attempts = 3
        for attempt in range(max_attempts):
            code = generate_code(settings.code_length)
            # Check for collision
            existing = await self.repo.get_url_by_code(self.conn, code)
            if existing is None:
                # Code is unique, insert
                await self.repo.insert_url(self.conn, code, original_url)
                short_url = f"{settings.base_url}/{code}"
                return {
                    "code": code,
                    "short_url": short_url,
                    "original_url": original_url,
                }
            logger.warning("Code collision: %s (attempt %d)", code, attempt + 1)
        raise HTTPException(status_code=500, detail="Failed to generate unique code after multiple attempts")
