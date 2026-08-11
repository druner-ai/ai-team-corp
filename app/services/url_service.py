import logging
from datetime import datetime, timezone
from app.repositories.url_repository import UrlRepository
from app.utils.slug_generator import generate_slug
from app.utils.url_validator import is_valid_url

logger = logging.getLogger(__name__)


class InvalidURLException(Exception):
    """Raised when the provided URL does not pass validation."""


class SlugAlreadyExistsException(Exception):
    """Raised when a custom slug is already taken."""


class MaxCollisionRetriesExceeded(Exception):
    """Raised when slug generation fails after several collision retries."""


class UrlService:
    """Business logic for creating, retrieving and soft-deleting short URLs."""

    def __init__(self, repo: UrlRepository):
        self.repo = repo

    async def create_url(self, conn, original_url: str, custom_slug: str | None = None) -> dict:
        """Create a short URL entry.

        Args:
            conn: Database connection.
            original_url: The long URL to shorten.
            custom_slug: Optional desired slug.

        Returns:
            dict with the new row data (id, slug, original_url, created_at, ...).

        Raises:
            InvalidURLException: URL scheme not allowed.
            SlugAlreadyExistsException: Custom slug already in use.
            MaxCollisionRetriesExceeded: Could not generate a unique slug.
        """
        if not is_valid_url(original_url):
            raise InvalidURLException(
                "The provided URL is invalid. Only http and https schemes are allowed."
            )

        slug = custom_slug
        if slug:
            exists = await self.repo.slug_exists(conn, slug)
            if exists:
                raise SlugAlreadyExistsException(f"Slug '{slug}' is already taken.")
        else:
            slug = await self._generate_unique_slug(conn)

        created_at = datetime.now(timezone.utc).isoformat()
        url_data = await self.repo.create(conn, slug, original_url, created_at)
        return url_data

    async def get_active_url(self, conn, slug: str) -> dict | None:
        """Return active URL data or None."""
        return await self.repo.get_active_by_slug(conn, slug)

    async def deactivate_url(self, conn, slug: str) -> bool:
        """Soft-delete a URL. Returns True if the URL was deactivated."""
        return await self.repo.deactivate(conn, slug)

    async def _generate_unique_slug(self, conn) -> str:
        max_attempts = 3
        for attempt in range(max_attempts):
            slug = generate_slug()
            exists = await self.repo.slug_exists(conn, slug)
            if not exists:
                return slug
            logger.warning(
                "Slug collision detected for '%s', attempt %d/%d",
                slug,
                attempt + 1,
                max_attempts,
            )
        raise MaxCollisionRetriesExceeded(
            "Failed to generate a unique slug after maximum retries."
        )
