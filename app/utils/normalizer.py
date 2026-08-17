import re

class Normalizer:
    @staticmethod
    def normalize(value: str) -> str:
        """Remove spaces, hyphens and convert to uppercase."""
        cleaned = re.sub(r'[\s-]', '', value)
        return cleaned.upper()
