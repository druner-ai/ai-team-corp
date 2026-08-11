"""
Short ID generator using Base62 encoding.
Generates a random 7-character string.
"""
import secrets
import string

BASE62_ALPHABET = string.ascii_letters + string.digits  # 62 chars
SHORT_ID_LENGTH = 7  # default, can be overridden


def generate_short_id(length: int = SHORT_ID_LENGTH) -> str:
    """
    Generate a cryptographically secure short ID from Base62 alphabet.
    Args:
        length: Number of characters (default 7)
    Returns:
        Random short_id string
    """
    return ''.join(secrets.choice(BASE62_ALPHABET) for _ in range(length))