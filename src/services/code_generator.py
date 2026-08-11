"""
Cryptographically secure short code generator using base62 encoding.

Generates URL-safe short codes from the alphabet [a-zA-Z0-9].
"""

import secrets
import string

# Base62 alphabet: lowercase + uppercase + digits (62 characters total)
ALPHABET = string.ascii_letters + string.digits


def generate_code(length: int = 6) -> str:
    """
    Generate a cryptographically secure random short code.

    Uses secrets.choice for cryptographic randomness, making the codes
    unpredictable and resistant to enumeration attacks.

    Args:
        length: The desired length of the short code. Default is 6.

    Returns:
        A random string of the specified length using base62 characters.
    """
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
