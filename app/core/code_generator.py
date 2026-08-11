import secrets
import string

ALPHABET = string.ascii_letters + string.digits  # a-z, A-Z, 0-9


def generate_code(length: int = 6) -> str:
    """
    Generate a cryptographically secure random alphanumeric code
    of the given length.
    """
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))
