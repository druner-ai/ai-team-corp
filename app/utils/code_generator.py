import secrets
import string

# Base62 character set: digits + uppercase + lowercase letters
BASE62_ALPHABET: str = string.digits + string.ascii_letters


def generate_short_code(length: int = 6) -> str:
    """
    Generate a cryptographically secure random short code using base62 alphabet.

    Args:
        length: Desired length of the code (default 6).

    Returns:
        Random string of specified length from [a-zA-Z0-9].

    Raises:
        ValueError: If length is less than 1.
    """
    if length < 1:
        raise ValueError("Length must be positive")
    return "".join(
        secrets.choice(BASE62_ALPHABET) for _ in range(length)
    )
