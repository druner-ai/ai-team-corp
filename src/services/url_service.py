"""
Business logic layer for URL shortening operations.

Orchestrates the repository and code generator to implement
create, redirect, and stats functionality.
"""

import logging
from typing import Any

import aiosqlite

from src.config import settings
from src.repositories.url_repository import URLRepository
from src.services.code_generator import generate_code

logger = logging.getLogger(__name__)


class URLService:
    """
    Service class for URL shortening business logic.

    Handles code generation with collision retry, redirect with click
    increment, and statistics retrieval.
    """

    def __init__(self, db: aiosqlite.Connection) -> None:
        """
        Initialize the URL service.

        Args:
            db: An active aiosqlite database connection.
        """
        self._repo = URLRepository(db)

    async def create_short_url(self, original_url: str) -> dict[str, Any]:
        """
        Create a short URL for the given original URL.

        Generates a unique short code with retry logic for collisions.

        Args:
            original_url: The original URL to shorten.

        Returns:
            A dict with short_code, short_url, and original_url.

        Raises:
            RuntimeError: If unable to generate a unique code after max retries.
        """
        for attempt in range(settings.max_retries):
            short_code = generate_code(settings.code_length)
            try:
                await self._repo.insert(short_code, original_url)
                logger.info(
                    "Created short URL: code=%s for url=%s",
                    short_code,
                    original_url,
                )
                return {
                    "short_code": short_code,
                    "short_url": f"{settings.base_url}/{short_code}",
                    "original_url": original_url,
                }
            except aiosqlite.IntegrityError:
                logger.warning(
                    "Collision detected for code=%s, attempt %d/%d",
                    short_code,
                    attempt + 1,
                    settings.max_retries,
                )
                continue

        raise RuntimeError(
            f"Failed to generate unique short code after {settings.max_retries} attempts"
        )

    async def redirect(self, short_code: str) -> str | None:
        """
        Resolve a short code to its original URL and increment click count.

        Args:
            short_code: The short code to look up.

        Returns:
            The original URL if found, None otherwise.
        """
        url_data = await self._repo.get_by_code(short_code)
        if url_data is None:
            return None

        await self._repo.increment_clicks(short_code)
        return url_data["original_url"]

    async def get_stats(self, short_code: str) -> dict[str, Any] | None:
        """
        Get statistics for a short code.

        Args:
            short_code: The short code to look up.

        Returns:
            A dict with short_code, original_url, clicks, and created_at,
            or None if not found.
        """
        url_data = await self._repo.get_by_code(short_code)
        if url_data is None:
            return None

        return {
            "short_code": url_data["short_code"],
            "original_url": url_data["original_url"],
            "clicks": url_data["clicks"],
            "created_at": url_data["created_at"],
        }
