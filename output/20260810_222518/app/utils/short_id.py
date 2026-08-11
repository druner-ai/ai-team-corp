"""
Short ID generation and validation utilities.
Uses base62 encoding for compact, URL-safe identifiers.
"""
import secrets
import string
from typing import Optional


# Base62 alphabet: a-z, A-Z, 0-9
BASE62_ALPHABET = string.ascii_lowercase + string.ascii_uppercase + string.digits
BASE62_LENGTH = len(BASE62_ALPHABET)  # 62


def _encode_base62(num: int) -> str:
    """
    Encode an integer to base62 string.
    
    Args:
        num: Integer to encode
        
    Returns:
        str: Base62 encoded string
    """
    if num == 0:
        return BASE62_ALPHABET[0]
    
    result = []
    while num > 0:
        num, remainder = divmod(num, BASE62_LENGTH)
        result.append(BASE62_ALPHABET[remainder])
    
    return "".join(reversed(result))


def generate_short_id(length: int = 7) -> str:
    """
    Generate a random short ID of specified length using base62 encoding.
    
    Uses cryptographically secure random number generator (secrets module)
    to generate random bytes, then encodes them in base62.
    
    Args:
        length: Desired length of the short ID (default: 7)
        
    Returns:
        str: Generated short ID
        
    Note:
        With 7 characters in base62, we get 62^7 ≈ 3.5 trillion combinations,
        which is sufficient to avoid collisions for reasonable volumes.
    """
    # Generate enough random bytes to cover the required length
    # Each byte gives 256 possibilities, we need 62^length
    # Using secrets.randbelow for uniform distribution
    max_value = BASE62_LENGTH ** length - 1
    random_num = secrets.randbelow(max_value + 1)
    
    # Encode to base62 and pad to required length
    encoded = _encode_base62(random_num)
    return encoded.zfill(length)


def validate_short_id(short_id: str, expected_length: int = 7) -> bool:
    """
    Validate that a short ID has the correct format.
    
    Args:
        short_id: The short ID to validate
        expected_length: Expected length of the short ID (default: 7)
        
    Returns:
        bool: True if valid, False otherwise
        
    Note:
        Valid short IDs contain only alphanumeric characters [a-zA-Z0-9]
        and have exactly the expected length.
    """
    if not short_id or len(short_id) != expected_length:
        return False
    
    return all(c in BASE62_ALPHABET for c in short_id)