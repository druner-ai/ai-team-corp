import hashlib

class Hasher:
    @staticmethod
    def hash(value: str) -> str:
        """Return SHA-256 hex digest of the value."""
        return hashlib.sha256(value.encode()).hexdigest()
