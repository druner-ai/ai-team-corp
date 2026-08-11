# Исправлено: добавлена функция init_db для создания таблиц, если они не существуют
# Это решает проблему 'no such table: urls' в тестах

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db():
    """Создаёт все таблицы в базе данных, если они ещё не существуют."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    """Генератор асинхронной сессии для внедрения зависимостей."""
    async with async_session() as session:
        yield session
