import string
import secrets
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import URL


def generate_short_code(length: int = 6) -> str:
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


async def create_short_url(db: AsyncSession, original_url: str) -> URL:
    # Generate unique short code
    while True:
        code = generate_short_code()
        result = await db.execute(select(URL).where(URL.short_code == code))
        if not result.scalar_one_or_none():
            break
    db_url = URL(short_code=code, original_url=original_url)
    db.add(db_url)
    await db.commit()
    await db.refresh(db_url)
    return db_url


async def get_url_by_code(db: AsyncSession, code: str) -> URL | None:
    result = await db.execute(select(URL).where(URL.short_code == code))
    return result.scalar_one_or_none()


async def increment_visits(db: AsyncSession, url: URL):
    from datetime import datetime
    stmt = (
        update(URL)
        .where(URL.id == url.id)
        .values(visits=URL.visits + 1, last_visited_at=datetime.utcnow())
    )
    await db.execute(stmt)
    await db.commit()
    # Refresh the object to reflect updated values
    await db.refresh(url)
