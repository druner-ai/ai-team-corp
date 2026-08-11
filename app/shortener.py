import secrets
import string
from app.config import settings

ALPHABET = string.ascii_letters + string.digits


def generate_short_code() -> str:
    """Генерирует случайный короткий код из букв и цифр длиной SHORT_CODE_LENGTH."""
    return ''.join(secrets.choice(ALPHABET) for _ in range(settings.short_code_length))


async def generate_unique_code(db) -> str:
    """Генерирует уникальный короткий код, делая до 3 попыток. Выбрасывает RuntimeError при неудаче."""
    from app.repository import get_url_by_code  # избегаем циркулярного импорта
    for _ in range(3):
        code = generate_short_code()
        existing = await get_url_by_code(db, code)
        if not existing:
            return code
    raise RuntimeError("Failed to generate unique short code after 3 attempts")
