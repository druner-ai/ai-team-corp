from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import URL


class URLRepository:
    """Репозиторий для работы с таблицей urls."""

    async def create(self, session: AsyncSession, slug: str, original_url: str) -> URL:
        """Создаёт новую запись URL."""
        url = URL(slug=slug, original_url=original_url)
        session.add(url)
        await session.commit()
        await session.refresh(url)
        return url

    async def get_by_slug(self, session: AsyncSession, slug: str) -> URL | None:
        """Возвращает URL по slug, если он существует и активен."""
        result = await session.execute(
            select(URL).where(URL.slug == slug, URL.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_by_slug_any(self, session: AsyncSession, slug: str) -> URL | None:
        """Возвращает URL по slug независимо от статуса активности."""
        result = await session.execute(select(URL).where(URL.slug == slug))
        return result.scalar_one_or_none()

    async def deactivate(self, session: AsyncSession, slug: str) -> bool:
        """Деактивирует URL по slug. Возвращает True, если запись была обновлена."""
        result = await session.execute(
            update(URL).where(URL.slug == slug).values(is_active=False)
        )
        await session.commit()
        return result.rowcount > 0
