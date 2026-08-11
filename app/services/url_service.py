"""
Business logic for URL shortening and management.

Orchestrates repository operations, caching, and code generation.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from app.repositories.url_repository import URLRepository
from app.cache.memory_cache import MemoryCache
from app.services.code_generator import CodeGenerator

logger = logging.getLogger(__name__)


class URLService:
    """
    Service layer for URL operations.

    Handles business logic: URL creation, retrieval, deactivation,
    click recording, and statistics.
    """

    def __init__(
        self,
        repository: URLRepository,
        cache: MemoryCache,
        base_url: str,
        short_code_length: int = 6,
    ) -> None:
        """
        Initialize the URL service.

        Args:
            repository: URLRepository instance for database operations.
            cache: MemoryCache instance for caching short codes.
            base_url: Base URL for constructing full short URLs.
            short_code_length: Length of generated short codes.
        """
        self._repository = repository
        self._cache = cache
        self._base_url = base_url.rstrip("/")
        self._code_generator = CodeGenerator(length=short_code_length)

    async def create_short_url(
        self,
        original_url: str,
        custom_code: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Create a new short URL.

        Args:
            original_url: The original URL to shorten.
            custom_code: Optional custom short code.
            expires_at: Optional expiration datetime.

        Returns:
            Dictionary with short URL details.

        Raises:
            ValueError: If the custom code is already taken.
        """
        if custom_code:
            # Check if custom code already exists
            existing = await self._repository.get_by_code(custom_code)
            if existing:
                raise ValueError(f"Custom code '{custom_code}' is already in use")
            short_code = custom_code
        else:
            # Generate a unique short code
            short_code = await self._generate_unique_code()

        now = datetime.now(timezone.utc)
        url_data = {
            "short_code": short_code,
            "original_url": original_url,
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat() if expires_at else None,
            "is_active": 1,
        }

        await self._repository.insert_url(url_data)

        # Cache the mapping
        self._cache.set(short_code, original_url)

        return {
            "short_code": short_code,
            "short_url": f"{self._base_url}/{short_code}",
            "original_url": original_url,
            "created_at": now,
            "expires_at": expires_at,
        }

    async def get_original_url(self, short_code: str) -> Optional[str]:
        """
        Retrieve the original URL for a given short code.

        Checks cache first, then falls back to database.
        Returns None if the link is not found, expired, or inactive.

        Args:
            short_code: The short code to look up.

        Returns:
            The original URL string, or None.
        """
        # Check cache first
        cached_url = self._cache.get(short_code)
        if cached_url:
            return cached_url

        # Fallback to database
        url_data = await self._repository.get_by_code(short_code)
        if url_data is None:
            return None

        # Check if active
        if not url_data.get("is_active"):
            return None

        # Check expiration
        expires_at = url_data.get("expires_at")
        if expires_at:
            try:
                exp_dt = datetime.fromisoformat(expires_at)
                if exp_dt < datetime.now(timezone.utc):
                    return None
            except (ValueError, TypeError):
                logger.warning(f"Invalid expires_at format for {short_code}: {expires_at}")
                return None

        original_url = url_data["original_url"]
        # Update cache
        self._cache.set(short_code, original_url)
        return original_url

    async def get_url_info(self, short_code: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a short URL.

        Args:
            short_code: The short code.

        Returns:
            Dictionary with URL info, or None if not found.
        """
        url_data = await self._repository.get_by_code(short_code)
        if url_data is None:
            return None

        stats = await self._repository.get_stats(url_data["id"])
        clicks_count = stats.get("clicks_count", 0) if stats else 0
        last_click_at = stats.get("last_click_at") if stats else None

        return {
            "short_code": url_data["short_code"],
            "short_url": f"{self._base_url}/{url_data['short_code']}",
            "original_url": url_data["original_url"],
            "created_at": datetime.fromisoformat(url_data["created_at"]),
            "expires_at": datetime.fromisoformat(url_data["expires_at"]) if url_data.get("expires_at") else None,
            "is_active": bool(url_data["is_active"]),
            "clicks_count": clicks_count,
            "last_click_at": datetime.fromisoformat(last_click_at) if last_click_at else None,
        }

    async def deactivate_url(self, short_code: str) -> bool:
        """
        Deactivate a short URL (soft delete).

        Args:
            short_code: The short code to deactivate.

        Returns:
            True if successful, False if not found.
        """
        url_data = await self._repository.get_by_code(short_code)
        if url_data is None:
            return False

        await self._repository.deactivate(url_data["id"])
        # Remove from cache
        self._cache.delete(short_code)
        return True

    async def record_click(
        self,
        short_code: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> None:
        """
        Record a click event for a short URL.

        This method is designed to be called as a fire-and-forget task.

        Args:
            short_code: The short code that was clicked.
            ip_address: Client IP address.
            user_agent: Client User-Agent header.
            referer: Referer header.
        """
        try:
            url_data = await self._repository.get_by_code(short_code)
            if url_data is None:
                logger.warning(f"Cannot record click: short_code '{short_code}' not found")
                return

            click_data = {
                "url_id": url_data["id"],
                "clicked_at": datetime.now(timezone.utc).isoformat(),
                "ip_address": ip_address,
                "user_agent": user_agent,
                "referer": referer,
            }
            await self._repository.insert_click(click_data)
        except Exception as e:
            logger.error(f"Failed to record click for {short_code}: {e}")

    async def get_url_stats(self, short_code: str, limit: int = 20) -> Optional[Dict[str, Any]]:
        """
        Get click statistics for a short URL.

        Args:
            short_code: The short code.
            limit: Maximum number of recent clicks to return.

        Returns:
            Dictionary with stats, or None if URL not found.
        """
        url_data = await self._repository.get_by_code(short_code)
        if url_data is None:
            return None

        stats = await self._repository.get_stats(url_data["id"])
        recent_clicks = await self._repository.get_recent_clicks(url_data["id"], limit=limit)

        clicks_count = stats.get("clicks_count", 0) if stats else 0
        last_click_at = stats.get("last_click_at") if stats else None

        return {
            "short_code": short_code,
            "clicks_count": clicks_count,
            "last_click_at": datetime.fromisoformat(last_click_at) if last_click_at else None,
            "created_at": datetime.fromisoformat(url_data["created_at"]),
            "recent_clicks": [
                {
                    "clicked_at": datetime.fromisoformat(click["clicked_at"]),
                    "ip_address": click.get("ip_address"),
                    "user_agent": click.get("user_agent"),
                    "referer": click.get("referer"),
                }
                for click in recent_clicks
            ],
        }

    async def _generate_unique_code(self) -> str:
        """
        Generate a unique short code.

        Uses a counter-based approach with base62 encoding.
        Retries with incremented counter on collision.

        Returns:
            A unique short code string.
        """
        max_attempts = 10
        for _ in range(max_attempts):
            code = self._code_generator.generate()
            existing = await self._repository.get_by_code(code)
            if existing is None:
                return code
        raise RuntimeError("Failed to generate unique short code after maximum attempts")
