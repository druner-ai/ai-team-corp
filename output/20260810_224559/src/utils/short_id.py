"""
Generator for short URL identifiers using Base62 encoding.

Algorithm: generate 7 random bytes, map each byte to a character
from the Base62 alphabet (0-9, a-z, A-Z) via modulo 62.
"""
import secrets

BASE62_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
SHORT_ID_LENGTH = 7


def generate_short_id() -> str:
    """
    Generate a random short ID consisting of 7 Base62 characters.

    Returns:
        A string of length 7.
    """
    random_bytes = secrets.token_bytes(SHORT_ID_LENGTH)
    # Map each byte to a character using modulo 62
    return "".join(BASE62_ALPHABET[b % 62] for b in random_bytes)  # type: ignore