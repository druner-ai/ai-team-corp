"""
Utility for generating unique short codes using base62.
"""
import secrets
import string

BASE62_ALPHABET = string.ascii_letters + string.digits  # a-z, A-Z, 0-9

def generate_code(length: int = 6) -> str:
    """
    Generate a cryptographically secure short code of given length.
    Uses secrets.choice for each character.
    """
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))