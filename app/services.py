"""Business logic for URL shortening.

Contains Base62 encoding for generating short codes from integer IDs.
"""

import string

# Base62 character set: 0-9, a-z, A-Z
BASE62_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
BASE62_LENGTH = len(BASE62_ALPHABET)


def encode_base62(num: int) -> str:
    """Encode an integer to a Base62 string.
    
    Args:
        num: Integer to encode (typically database row ID).
        
    Returns:
        Base62 encoded string.
    """
    if num == 0:
        return BASE62_ALPHABET[0]
    
    result = []
    while num > 0:
        num, remainder = divmod(num, BASE62_LENGTH)
        result.append(BASE62_ALPHABET[remainder])
    
    return ''.join(reversed(result))
