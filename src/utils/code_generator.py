"""
Utility for generating short codes using base62 alphabet.
"""
import secrets

# Base62 alphabet: a-z, A-Z, 0-9
ALPHABET = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"


def generate_code(length: int = 6) -> str:
    """
    Generate a cryptographically secure random short code.
    Uses secrets.choice for unbiased randomness.
    """
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
