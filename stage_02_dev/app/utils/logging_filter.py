import logging
import re

class MaskingFilter(logging.Filter):
    """Filter that masks sequences of 13-34 alphanumeric characters."""
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self._mask_text(record.msg)
        if record.args:
            record.args = tuple(self._mask_text(str(a)) if isinstance(a, str) else a for a in record.args)
        return True

    def _mask_text(self, text: str) -> str:
        pattern = re.compile(r'[A-Z0-9]{13,34}')
        def replacer(match):
            s = match.group(0)
            if len(s) < 8:
                return s
            return s[:4] + '*' * (len(s) - 8) + s[-4:]
        return pattern.sub(replacer, text)
