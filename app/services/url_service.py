import logging
from app.database import DatabaseManager
from app.utils.code_generator import generate_short_code
from app.config import settings

logger = logging.getLogger(__name__)


class URLService:
    """Business logic for URL shortening and retrieval."""

    def __init__(self, db: DatabaseManager):
        self._db = db

    async def create_short_link(self, original_url: str) -> dict:
        """
        Create a new short link or return existing one if URL already exists.
        Returns a dict with keys: short_code, short_url, original_url, created_at.
        """
        # Check if URL already exists
        existing = await self._db.fetchone(
            "SELECT short_code, original_url, created_at FROM links WHERE original_url = ?",
            (original_url,),
        )
        if existing:
            logger.info(f"Found existing short link for URL: {original_url}")
            return {
                "short_code": existing["short_code"],
                "short_url": f"{settings.base_url}/{existing['short_code']}",
                "original_url": existing["original_url"],
                "created_at": existing["created_at"],
            }

        # Generate unique code
        max_attempts = 5
        for attempt in range(max_attempts):
            code = generate_short_code(settings.short_code_length)
            # Check if code exists
            code_exists = await self._db.fetchone(
                "SELECT id FROM links WHERE short_code = ?", (code,)
            )
            if not code_exists:
                break
            logger.warning(f"Code collision detected: {code}, attempt {attempt+1}")
        else:
            logger.error("Failed to generate unique short code after multiple attempts")
            raise RuntimeError("Failed to generate unique short code after multiple attempts")

        # Insert new record
        await self._db.execute(
            "INSERT INTO links (short_code, original_url) VALUES (?, ?)",
            (code, original_url),
        )
        # Retrieve created_at for response
        row = await self._db.fetchone(
            "SELECT created_at FROM links WHERE short_code = ?", (code,)
        )
        created_at = row["created_at"] if row else None
        logger.info(f"Created short link: {code} -> {original_url}")
        return {
            "short_code": code,
            "short_url": f"{settings.base_url}/{code}",
            "original_url": original_url,
            "created_at": created_at,
        }

    async def get_original_url(self, short_code: str) -> str | None:
        """Return original URL or None if not found."""
        row = await self._db.fetchone(
            "SELECT original_url FROM links WHERE short_code = ?", (short_code,)
        )
        return row["original_url"] if row else None
