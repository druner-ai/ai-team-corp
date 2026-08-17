"""ASSERT-02: маскирование в логах — полные реквизиты 13–34 символа заменяются маской.

Исправлено: фильтр теперь использует Masker.mask() для маскирования, что гарантирует
единообразие маскирования в логах и API. Ранее использовалась собственная логика,
которая давала неправильное количество звёздочек.
"""

import logging
import re
from app.utils.masker import Masker


class MaskingFilter(logging.Filter):
    """Фильтр логирования, маскирующий чувствительные данные."""

    # Паттерн: последовательности из 13–34 заглавных букв и цифр (IBAN, номера карт)
    SENSITIVE_PATTERN = re.compile(r'\b[A-Z0-9]{13,34}\b')

    def filter(self, record: logging.LogRecord) -> bool:
        """Маскирует чувствительные данные в сообщении лога."""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self.SENSITIVE_PATTERN.sub(
                lambda m: Masker.mask(m.group()),
                record.msg
            )
        return True
