"""
    Base62 encoding/decoding.
    Uses characters A-Z, a-z, 0-9.
"""
import string
import secrets

ALPHABET = string.ascii_uppercase + string.ascii_lowercase + string.digits
BASE = 62

def encode_base62(num: int) -> str:
    if num == 0:
        return ALPHABET[0]
    arr = []
    while num:
        num, rem = divmod(num, BASE)
        arr.append(ALPHABET[rem])
    arr.reverse()
    return ''.join(arr)

def decode_base62(s: str) -> int:
    num = 0
    for char in s:
        num = num * BASE + ALPHABET.index(char)
    return num

def generate_random_id(length: int = 7) -> str:
    """Generate a random Base62 string of given length."""
    return ''.join(secrets.choice(ALPHABET) for _ in range(length))