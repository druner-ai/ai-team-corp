import secrets
import string

BASE62_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase


def generate_code(length: int = 6) -> str:
    """Generate a random base62 string of the given length."""
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))
