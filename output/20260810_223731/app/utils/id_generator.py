"""
Functions for generating and encoding short base62 IDs.
"""
import string
import secrets   # <-- changed from random for cryptographically strong randomness

# Base62 alphabet (alphanumeric)
BASE62_ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits
BASE62_LEN = len(BASE62_ALPHABET)  # 62
SHORT_ID_LENGTH = 7
MAX_ID_VALUE = BASE62_LEN**SHORT_ID_LENGTH  # 62^7 ≈ 3.5 trillion


def encode_base62(num: int) -> str:
    """Encode an integer into base62 string (without padding)."""
    if num == 0:
        return BASE62_ALPHABET[0]
    chars = []
    while num > 0:
        num, remainder = divmod(num, BASE62_LEN)
        chars.append(BASE62_ALPHABET[remainder])
    return "".join(reversed(chars))


def generate_short_id() -> str:
    """
    Generate a random 7-character base62 ID using a secure RNG.
    """
    rand_int = secrets.randbelow(MAX_ID_VALUE)   # cryptographically strong
    encoded = encode_base62(rand_int)
    return encoded.rjust(SHORT_ID_LENGTH, BASE62_ALPHABET[0])