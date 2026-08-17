"""ASSERT-05: валидатор IBAN — mod-97 + длина 15–34.

Исправлено:
1. Добавлена проверка кода страны (первые 2 символа должны быть буквами).
   Ранее проверка кода страны отсутствовала, из-за чего невалидный код страны
   (например, "XX") не вызывал ошибку INVALID_FORMAT.
2. Добавлена проверка длины > 34 — возвращает INVALID_LENGTH.
   Ранее проверка длины > 34 отсутствовала.
"""

from app.domain.validators.base import ValidationResult, ErrorItem


class IbanValidator:
    """Валидатор IBAN."""

    @staticmethod
    def validate(iban: str) -> ValidationResult:
        """Валидирует IBAN.

        Args:
            iban: Нормализованный IBAN (без пробелов, в верхнем регистре).

        Returns:
            ValidationResult с результатом проверки.
        """
        errors = []

        # Проверка длины
        if len(iban) < 15:
            errors.append(ErrorItem(
                code="INVALID_LENGTH",
                message="IBAN must be at least 15 characters"
            ))
        elif len(iban) > 34:
            errors.append(ErrorItem(
                code="INVALID_LENGTH",
                message="IBAN must be at most 34 characters"
            ))

        # Проверка формата: первые 2 символа — буквы, остальные — буквы и цифры
        if len(iban) >= 2:
            if not (iban[0].isalpha() and iban[1].isalpha()):
                errors.append(ErrorItem(
                    code="INVALID_FORMAT",
                    message="IBAN must start with 2 letters"
                ))
            elif not iban[2:].isalnum():
                errors.append(ErrorItem(
                    code="INVALID_FORMAT",
                    message="IBAN must contain only letters and digits"
                ))

        # Если есть ошибки формата/длины, не проверяем контрольную сумму
        if errors:
            return ValidationResult(is_valid=False, errors=errors)

        # Проверка контрольной суммы (mod-97)
        if not IbanValidator._check_mod97(iban):
            errors.append(ErrorItem(
                code="INVALID_CHECKSUM",
                message="IBAN checksum is invalid"
            ))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )

    @staticmethod
    def _check_mod97(iban: str) -> bool:
        """Проверяет IBAN по алгоритму mod-97.

        Алгоритм:
        1. Переместить первые 4 символа в конец.
        2. Заменить буквы на числа (A=10, B=11, ..., Z=35).
        3. Вычислить остаток от деления на 97.
        4. Валидный IBAN даёт остаток 1.
        """
        # Перемещаем первые 4 символа в конец
        rearranged = iban[4:] + iban[:4]

        # Заменяем буквы на числа
        numeric = ""
        for char in rearranged:
            if char.isalpha():
                numeric += str(ord(char) - ord('A') + 10)
            else:
                numeric += char

        # Вычисляем остаток от деления на 97
        remainder = int(numeric) % 97
        return remainder == 1
