"""
Base62 encoding/decoding utilities.

Base62 uses characters: 0-9, a-z, A-Z (62 characters total).
This is used for generating short codes from integer IDs.
"""

import string

# Base62 alphabet
BASE62_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
BASE62_BASE = len(BASE62_ALPHABET)  # 62

# Character to index mapping for decoding
_BASE62_CHAR_TO_INDEX = {char: idx for idx, char in enumerate(BASE62_ALPHABET)}


def encode_base62(number: int) -> str:
    """
    Encode an integer to a base62 string.

    Args:
        number: Non-negative integer to encode.

    Returns:
        Base62 encoded string.

    Raises:
        ValueError: If number is negative.

    Examples:
        >>> encode_base62(0)
        '0'
        >>> encode_base62(61)
        'Z'
        >>> encode_base62(62)
        '10'
    """
    if number < 0:
        raise ValueError("Number must be non-negative")

    if number == 0:
        return BASE62_ALPHABET[0]

    result = []
    while number > 0:
        number, remainder = divmod(number, BASE62_BASE)
        result.append(BASE62_ALPHABET[remainder])

    return "".join(reversed(result))


def decode_base62(encoded: str) -> int:
    """
    Decode a base62 string back to an integer.

    Args:
        encoded: Base62 encoded string.

    Returns:
        Decoded integer.

    Raises:
        ValueError: If string contains invalid characters.

    Examples:
        >>> decode_base62('0')
        0
        >>> decode_base62('Z')
        61
        >>> decode_base62('10')
        62
    """
    if not encoded:
        raise ValueError("Encoded string must not be empty")

    result = 0
    for char in encoded:
        if char not in _BASE62_CHAR_TO_INDEX:
            raise ValueError(f"Invalid base62 character: '{char}'")
        result = result * BASE62_BASE + _BASE62_CHAR_TO_INDEX[char]

    return result