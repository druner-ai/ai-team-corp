from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Click


class ClickRepository:
    """Репозиторий для работы с таблицей clicks."""

    async def create(self, session: AsyncSession, slug: str, ip_address: str | None = None) -> Click:
        """Записывает клик по короткой ссылке."""
        click = Click(slug=slug, ip_address=ip_address)
        session.add(click)
        await session.commit()
        await session.refresh(click)
        return click

    async def get_count_by_slug(self, session: AsyncSession, slug: str) -> int:
        """Возвращает количество кликов по slug."""
        result = await session.execute(
            select(func.count()).select_from(Click).where(Click.slug == slug)
        )
        return result.scalar() or 0

    async def get_all_by_slug(self, session: AsyncSession, slug: str) -> list[Click]:
        """Возвращает все записи кликов по slug."""
        result = await session.execute(
            select(Click).where(Click.slug == slug).order_by(Click.clicked_at.desc())
        )
        return list(result.scalars().all())
