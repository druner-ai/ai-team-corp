"""Base62 encoding and random code generation."""

import secrets
import string

BASE62_ALPHABET = string.ascii_letters + string.digits  # a-z, A-Z, 0-9


def id_to_code(num: int, length: int = 6) -> str:
    """
    Encode an integer ID into a base62 string of fixed length.
    Pads with leading 'a' characters if necessary.
    """
    if num < 0:
        raise ValueError("ID must be non-negative")
    chars = []
    while num > 0:
        num, rem = divmod(num, 62)
        chars.append(BASE62_ALPHABET[rem])
    code = "".join(reversed(chars)) if chars else BASE62_ALPHABET[0]
    # Pad to desired length
    if len(code) < length:
        code = BASE62_ALPHABET[0] * (length - len(code)) + code
    return code


def generate_random_code(length: int = 6) -> str:
    """Generate a cryptographically random base62 code."""
    return "".join(secrets.choice(BASE62_ALPHABET) for _ in range(length))
