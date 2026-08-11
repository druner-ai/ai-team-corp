import logging
from app.repositories.url_repository import UrlRepository
from app.repositories.stats_repository import StatsRepository

logger = logging.getLogger(__name__)


class UrlNotFoundForStats(Exception):
    """Raised when a slug is not found or is inactive."""


class StatsService:
    """Business logic for recording clicks and serving statistics."""

    def __init__(self, url_repo: UrlRepository, stats_repo: StatsRepository):
        self.url_repo = url_repo
        self.stats_repo = stats_repo

    async def record_click_background(
        self,
        slug: str,
        ip: str | None,
        ua: str | None,
        referer: str | None,
    ) -> None:
        """Record a click as a background task using a separate connection."""
        from app.database import get_connection
        from datetime import datetime, timezone

        conn = await get_connection()
        try:
            url_data = await self.url_repo.get_active_by_slug(conn, slug)
            if url_data is None:
                logger.warning(
                    "Cannot record click: slug '%s' not found or inactive.", slug
                )
                return
            url_id = url_data["id"]
            clicked_at = datetime.now(timezone.utc).isoformat()
            await self.stats_repo.record_click(
                conn, url_id, clicked_at, ip, ua, referer
            )
        except Exception as e:
            logger.error("Failed to record click for slug '%s': %s", slug, e)
        finally:
            await conn.close()

    async def get_url_stats(self, conn, slug: str, max_recent: int) -> dict:
        """Retrieve combined stats for a slug.

        Returns:
            dict with keys 'url_data', 'total_clicks', 'recent_clicks'.
        """
        url_data = await self.url_repo.get_active_by_slug(conn, slug)
        if url_data is None:
            raise UrlNotFoundForStats(
                f"URL with slug '{slug}' not found or inactive."
            )
        url_id = url_data["id"]
        total = await self.stats_repo.get_total_clicks(conn, url_id)
        recent = await self.stats_repo.get_recent_clicks(conn, url_id, max_recent)
        return {
            "url_data": url_data,
            "total_clicks": total,
            "recent_clicks": recent,
        }
