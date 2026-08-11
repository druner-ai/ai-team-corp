import secrets
import string
from app.config import settings

ALPHABET = string.ascii_letters + string.digits


def generate_slug(length: int | None = None) -> str:
    """Generate a cryptographically random slug.

    Args:
        length: Number of characters (defaults to settings.SLUG_LENGTH).

    Returns:
        A random string of the given length consisting of letters and digits.
    """
    if length is None:
        length = settings.slug_length
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))
