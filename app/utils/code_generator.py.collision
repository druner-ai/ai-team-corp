"""
Cryptographically secure short code generator.

Uses secrets.choice for randomness suitable for security-sensitive contexts.
"""

import secrets
import string

# Alphanumeric alphabet: a-z, A-Z, 0-9 (62 characters)
_ALPHABET = string.ascii_letters + string.digits


def generate_code(length: int = 6) -> str:
    """
    Generate a random short code of the specified length.

    Uses secrets.choice for cryptographically strong randomness.

    Args:
        length: Desired code length (default 6).

    Returns:
        A random string of alphanumeric characters.
    """
    return "".join(secrets.choice(_ALPHABET) for _ in range(length))
