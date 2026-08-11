import logging
from typing import Dict, Any
import aiosqlite

from app.config import settings
from app.core.code_generator import generate_code
from app.repositories.url_repository import create_url, get_url_by_code

logger = logging.getLogger(__name__)

MAX_COLLISION_RETRIES = 5


async def create_short_url(
    db: aiosqlite.Connection, original_url: str
) -> Dict[str, Any]:
    """
    Generate a unique short code and persist the short URL.
    Retries on code collision up to MAX_COLLISION_RETRIES times.
    """
    for attempt in range(MAX_COLLISION_RETRIES):
        code = generate_code(settings.code_length)
        existing = await get_url_by_code(db, code)
        if existing is None:
            record = await create_url(db, code, original_url)
            short_url = f"{settings.base_url}/{code}"
            return {
                "code": code,
                "short_url": short_url,
                "original_url": original_url,
            }
        logger.warning(
            "Collision for code %s, retry %d/%d",
            code,
            attempt + 1,
            MAX_COLLISION_RETRIES,
        )
    raise RuntimeError(
        "Failed to generate unique short code after maximum retries"
    )
