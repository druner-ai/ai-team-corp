import secrets
import string

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.repositories.url_repository import URLRepository


class URLService:
    """Сервисный слой для бизнес-логики работы с URL."""

    def __init__(self, repo: URLRepository | None = None):
        self.repo = repo or URLRepository()

    @staticmethod
    def generate_slug(length: int = None) -> str:
        """Генерирует случайный slug заданной длины."""
        length = length or settings.slug_length
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    async def create_url(self, session: AsyncSession, original_url: str, custom_slug: str | None = None) -> dict:
        """Создаёт короткую ссылку. Если custom_slug задан, проверяет его уникальность."""
        if custom_slug:
            existing = await self.repo.get_by_slug_any(session, custom_slug)
            if existing:
                raise ValueError(f"Slug '{custom_slug}' already exists")
            slug = custom_slug
        else:
            slug = self.generate_slug()
            # Гарантируем уникальность сгенерированного slug
            while await self.repo.get_by_slug_any(session, slug):
                slug = self.generate_slug()

        url = await self.repo.create(session, slug, original_url)
        return {
            "slug": url.slug,
            "original_url": url.original_url,
            "short_url": f"{settings.base_url}/{url.slug}",
            "created_at": url.created_at.isoformat(),
        }

    async def get_url(self, session: AsyncSession, slug: str) -> dict | None:
        """Возвращает данные URL по slug."""
        url = await self.repo.get_by_slug(session, slug)
        if not url:
            return None
        return {
            "slug": url.slug,
            "original_url": url.original_url,
            "short_url": f"{settings.base_url}/{url.slug}",
            "created_at": url.created_at.isoformat(),
            "is_active": url.is_active,
        }

    async def deactivate_url(self, session: AsyncSession, slug: str) -> bool:
        """Деактивирует URL по slug."""
        return await self.repo.deactivate(session, slug)
