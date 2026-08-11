"""
Short code generator using base62 encoding.

Generates unique short codes from an auto-incrementing counter.
"""

import string
import threading


class CodeGenerator:
    """
    Generates short codes using base62 encoding of a counter.

    Thread-safe counter increment with base62 conversion.
    """

    BASE62_ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
    BASE = len(BASE62_ALPHABET)  # 62

    def __init__(self, length: int = 6, offset: int = 0) -> None:
        """
        Initialize the code generator.

        Args:
            length: Minimum length of generated codes (padded with leading zeros).
            offset: Initial counter offset to avoid very short codes.
        """
        self._length = length
        self._counter = offset
        self._lock = threading.Lock()

    def generate(self) -> str:
        """
        Generate the next short code.

        Increments the internal counter and encodes it in base62.
        The result is zero-padded to the configured length.

        Returns:
            A base62-encoded short code string.
        """
        with self._lock:
            self._counter += 1
            return self._encode(self._counter)

    def _encode(self, num: int) -> str:
        """
        Encode an integer to a base62 string.

        Args:
            num: The integer to encode.

        Returns:
            Base62-encoded string, zero-padded to minimum length.
        """
        if num == 0:
            result = self.BASE62_ALPHABET[0]
        else:
            chars = []
            while num > 0:
                num, rem = divmod(num, self.BASE)
                chars.append(self.BASE62_ALPHABET[rem])
            result = "".join(reversed(chars))

        # Pad to minimum length
        if len(result) < self._length:
            result = result.zfill(self._length)
        return result
