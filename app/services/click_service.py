from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.click_repository import ClickRepository


class ClickService:
    """Сервисный слой для бизнес-логики работы с кликами."""

    def __init__(self, repo: ClickRepository | None = None):
        self.repo = repo or ClickRepository()

    async def record_click(self, session: AsyncSession, slug: str, ip_address: str | None = None) -> dict:
        """Записывает клик и возвращает его данные."""
        click = await self.repo.create(session, slug, ip_address)
        return {
            "id": click.id,
            "slug": click.slug,
            "clicked_at": click.clicked_at.isoformat(),
            "ip_address": click.ip_address,
        }

    async def get_stats(self, session: AsyncSession, slug: str) -> dict | None:
        """Возвращает статистику по slug."""
        count = await self.repo.get_count_by_slug(session, slug)
        clicks = await self.repo.get_all_by_slug(session, slug)
        return {
            "slug": slug,
            "total_clicks": count,
            "clicks": [
                {
                    "clicked_at": c.clicked_at.isoformat(),
                    "ip_address": c.ip_address,
                }
                for c in clicks
            ],
        }
