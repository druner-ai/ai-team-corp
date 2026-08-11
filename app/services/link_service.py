import re
from app.repositories import link_repository, click_repository
from app.cache import TTLCache
from app.database import DatabasePool
from app.schemas import LinkResponse, StatsResponse
from app.utils import generate_slug
from app.config import BASE_URL
import logging

logger = logging.getLogger(__name__)


class LinkService:
    """Business logic for link operations."""

    def __init__(self, db_pool: DatabasePool, cache: TTLCache):
        self.db_pool = db_pool
        self.cache = cache

    async def create_link(self, url: str, custom_slug: str = None) -> LinkResponse:
        slug = custom_slug
        if slug:
            if not re.match(r'^[a-zA-Z0-9_-]{1,20}$', slug):
                logger.warning(f"Invalid custom slug format: {slug}")
                raise ValueError("Custom slug must be 1-20 alphanumeric characters, hyphens or underscores")
            async with self.db_pool.acquire() as conn:
                existing = await link_repository.get_link_by_slug(conn, slug)
                if existing:
                    logger.warning(f"Duplicate custom slug: {slug}")
                    raise ValueError(f"Slug '{slug}' already exists")
        else:
            # Generate unique slug (up to 5 attempts)
            for _ in range(5):
                slug = generate_slug()
                async with self.db_pool.acquire() as conn:
                    existing = await link_repository.get_link_by_slug(conn, slug)
                    if not existing:
                        break
            else:
                logger.error("Failed to generate unique slug after 5 attempts")
                raise RuntimeError("Failed to generate unique slug after 5 attempts")

        async with self.db_pool.acquire() as conn:
            await link_repository.insert_link(conn, slug, url)
            link = await link_repository.get_link_by_slug(conn, slug)
        # Invalidate cache (though new slug won't be cached)
        self.cache.delete(slug)
        return LinkResponse(
            slug=link['slug'],
            short_url=f"{BASE_URL}/{link['slug']}",
            original_url=link['original_url'],
            created_at=link['created_at']
        )

    async def resolve_link(self, slug: str) -> str | None:
        # Check cache first
        cached_url = self.cache.get(slug)
        if cached_url:
            return cached_url
        async with self.db_pool.acquire() as conn:
            link = await link_repository.get_link_by_slug(conn, slug)
            if link:
                self.cache.set(slug, link['original_url'])
                return link['original_url']
        return None

    async def record_click(self, slug: str, ip_address: str = None, user_agent: str = None):
        async with self.db_pool.acquire() as conn:
            link = await link_repository.get_link_by_slug(conn, slug)
            if link:
                await click_repository.insert_click(conn, link['id'], ip_address, user_agent)

    async def get_stats(self, slug: str) -> StatsResponse | None:
        async with self.db_pool.acquire() as conn:
            stats = await click_repository.get_stats_by_slug(conn, slug)
            if stats:
                return StatsResponse(
                    slug=stats['slug'],
                    original_url=stats['original_url'],
                    created_at=stats['created_at'],
                    clicks_count=stats['clicks_count'],
                    last_click_at=stats['last_click_at'],
                    last_click_ip=stats['last_click_ip'],
                    last_click_user_agent=stats['last_click_user_agent']
                )
        return None
