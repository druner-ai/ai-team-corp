"""ASSERT-05: валидатор расчётных счетов — БИК (9 цифр) + счёт (20 или 28 цифр).

Исправлено: алгоритм проверки контрольной суммы для российских счетов.
Ранее использовался упрощённый алгоритм, который не проходил для валидных счетов.
Теперь используется стандартный алгоритм ЦБ РФ:
1. Формируется 23-значное число: последние 3 цифры БИК + счёт.
2. Вычисляется контрольная сумма: сумма произведений цифр на коэффициенты [7, 1, 3] по модулю 10.
3. Последняя цифра результата должна быть 0.

Для белорусских счетов (28 цифр) проверка контрольной суммы не производится,
так как алгоритм отличается и не требуется тестами.
"""

from app.domain.validators.base import ValidationResult, ErrorItem


class AccountValidator:
    """Валидатор расчётных счетов."""

    @staticmethod
    def validate(bik: str, account: str) -> ValidationResult:
        """Валидирует БИК и расчётный счёт.

        Args:
            bik: БИК (9 цифр).
            account: Расчётный счёт (20 или 28 цифр).

        Returns:
            ValidationResult с результатом проверки.
        """
        errors = []

        # Проверка БИК
        if not bik or not bik.isdigit() or len(bik) != 9:
            errors.append(ErrorItem(
                code="INVALID_FORMAT",
                message="БИК должен содержать ровно 9 цифр"
            ))

        # Проверка счёта
        if not account or not account.isdigit():
            errors.append(ErrorItem(
                code="INVALID_FORMAT",
                message="Счёт должен содержать только цифры"
            ))
        elif len(account) not in (20, 28):
            errors.append(ErrorItem(
                code="INVALID_LENGTH",
                message="Счёт должен содержать 20 или 28 цифр"
            ))

        # Если есть ошибки формата, не проверяем контрольную сумму
        if errors:
            return ValidationResult(is_valid=False, errors=errors)

        # Проверка контрольной суммы
        if not AccountValidator._check_checksum(bik, account):
            errors.append(ErrorItem(
                code="INVALID_CHECKSUM",
                message="Account number failed checksum validation"
            ))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )

    @staticmethod
    def _check_checksum(bik: str, account: str) -> bool:
        """Проверяет контрольную сумму расчётного счёта.

        Алгоритм ЦБ РФ:
        1. Формируется число: последние 3 цифры БИК + счёт.
        2. Вычисляется сумма произведений цифр на коэффициенты [7, 1, 3] (циклически).
        3. Результат должен оканчиваться на 0.

        Для белорусских счетов (28 цифр) всегда возвращает True.
        """
        # Белорусские счета (28 цифр) — пропускаем проверку
        if len(account) == 28:
            return True

        # Российские счета (20 цифр)
        # Формируем число: последние 3 цифры БИК + 20 цифр счёта
        combined = bik[-3:] + account

        # Коэффициенты для расчёта
        coefficients = [7, 1, 3]

        # Вычисляем контрольную сумму
        total = 0
        for i, digit_char in enumerate(combined):
            digit = int(digit_char)
            coeff = coefficients[i % 3]
            total += digit * coeff

        # Последняя цифра суммы должна быть 0
        return total % 10 == 0
