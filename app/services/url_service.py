"""Business logic for URL shortening."""

import aiosqlite

from app.config import settings
from app.db.repository import insert_url, get_url_by_code
from app.utils.code_generator import id_to_code, generate_random_code


class URLService:
    """Service for creating and retrieving short URLs."""

    def __init__(self, db: aiosqlite.Connection) -> None:
        self.db = db

    async def create_short_url(self, original_url: str) -> dict:
        """
        Create a new short URL entry.

        Strategy:
        1. Insert a new row to obtain an auto-incremented ID.
        2. Encode the ID into a base62 short code.
        3. Update the row with the generated short code.
        4. If a collision occurs (extremely unlikely), fall back to random code generation.
        """
        # Insert a placeholder to get the ID
        cursor = await self.db.execute(
            "INSERT INTO urls (original_url) VALUES (?)", (original_url,)
        )
        row_id = cursor.lastrowid
        await self.db.commit()

        # Generate short code from ID
        short_code = id_to_code(row_id, settings.short_code_length)

        # Update the row with the short code
        try:
            await self.db.execute(
                "UPDATE urls SET short_code = ? WHERE id = ?", (short_code, row_id)
            )
            await self.db.commit()
        except aiosqlite.IntegrityError:
            # Collision – fallback to random code
            await self.db.rollback()
            short_code = await self._generate_unique_code()
            await self.db.execute(
                "UPDATE urls SET short_code = ? WHERE id = ?", (short_code, row_id)
            )
            await self.db.commit()

        short_url = f"{settings.base_url.rstrip('/')}/{short_code}"
        return {
            "short_code": short_code,
            "short_url": short_url,
            "original_url": original_url,
        }

    async def get_original_url(self, short_code: str) -> str | None:
        """Retrieve the original URL for a given short code."""
        row = await get_url_by_code(self.db, short_code)
        if row is None:
            return None
        return row["original_url"]

    async def _generate_unique_code(self) -> str:
        """Generate a random unique short code with up to 3 attempts."""
        for _ in range(3):
            code = generate_random_code(settings.short_code_length)
            existing = await get_url_by_code(self.db, code)
            if existing is None:
                return code
        raise RuntimeError("Failed to generate a unique short code after 3 attempts")
