"""
Business logic for URL shortening, redirect, and statistics.

Orchestrates calls to the repository layer and handles code generation.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import Depends

from app.config import settings
from app.repositories.url_repository import UrlRepository, get_url_repository
from app.utils.code_generator import generate_code

logger = logging.getLogger(__name__)


class UrlService:
    """
    Service layer for URL operations.

    Encapsulates business logic and coordinates between routers and the repository.
    """

    def __init__(self, repository: UrlRepository) -> None:
        """
        Initialize the service with a repository instance.

        Args:
            repository: Data access layer for URL operations.
        """
        self._repo = repository

    async def create_short_url(self, original_url: str) -> dict[str, Any]:
        """
        Create a new short URL entry.

        Generates a unique code (up to max attempts), persists the record,
        and returns the response data.

        Args:
            original_url: The validated original URL.

        Returns:
            Dict with keys: code, short_url, original_url.

        Raises:
            RuntimeError: If a unique code cannot be generated after max attempts.
        """
        for attempt in range(1, settings.MAX_CODE_GENERATION_ATTEMPTS + 1):
            code = generate_code(settings.CODE_LENGTH)
            existing = await self._repo.find_by_code(code)
            if existing is None:
                created_at = datetime.now(timezone.utc).isoformat()
                await self._repo.insert_url(code, original_url, created_at)
                logger.info(
                    "Created short URL: code=%s, original=%s, attempt=%d",
                    code,
                    original_url,
                    attempt,
                )
                return {
                    "code": code,
                    "short_url": f"{settings.BASE_URL}/{code}",
                    "original_url": original_url,
                }
            logger.warning(
                "Code collision: code=%s already exists, attempt=%d",
                code,
                attempt,
            )

        raise RuntimeError(
            f"Failed to generate unique code after {settings.MAX_CODE_GENERATION_ATTEMPTS} attempts."
        )

    async def get_original_url_and_increment_clicks(
        self,
        code: str,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str | None:
        """
        Look up the original URL by code, increment the click counter, and log the click.

        Args:
            code: The short code.
            ip_address: Client IP address (optional).
            user_agent: Client User-Agent header (optional).

        Returns:
            The original URL string if found, otherwise None.
        """
        url_record = await self._repo.find_by_code(code)
        if url_record is None:
            return None

        clicked_at = datetime.now(timezone.utc).isoformat()
        await self._repo.increment_clicks(code)
        await self._repo.insert_click(
            url_id=url_record["id"],
            clicked_at=clicked_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        logger.debug("Redirect: code=%s -> %s", code, url_record["original_url"])
        return url_record["original_url"]

    async def get_stats(self, code: str) -> dict[str, Any] | None:
        """
        Retrieve statistics for a given short code.

        Args:
            code: The short code.

        Returns:
            Dict with keys: code, original_url, created_at, clicks, or None if not found.
        """
        url_record = await self._repo.find_by_code(code)
        if url_record is None:
            return None

        return {
            "code": url_record["code"],
            "original_url": url_record["original_url"],
            "created_at": datetime.fromisoformat(url_record["created_at"]),
            "clicks": url_record["clicks"],
        }


def get_url_service(repository: UrlRepository = Depends(get_url_repository)) -> UrlService:
    """
    FastAPI dependency that provides a UrlService instance.

    Args:
        repository: Injected repository instance.

    Returns:
        Configured UrlService.
    """
    return UrlService(repository)
