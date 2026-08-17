class Masker:
    @staticmethod
    def mask(value: str) -> str:
        """Return first 4 + asterisks + last 4 characters."""
        if len(value) < 8:
            return value
        return value[:4] + '*' * (len(value) - 8) + value[-4:]
