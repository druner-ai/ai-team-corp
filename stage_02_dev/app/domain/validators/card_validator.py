from app.domain.validators.models import ValidationResult, ErrorItem

class CardValidator:
    @staticmethod
    def validate(normalized: str) -> ValidationResult:
        errors = []
        if not normalized:
            errors.append(ErrorItem("INVALID_LENGTH", "Card number is empty"))
            return ValidationResult(False, errors)
        if not normalized.isdigit():
            errors.append(ErrorItem("INVALID_FORMAT", "Card number must contain only digits"))
            return ValidationResult(False, errors)
        if len(normalized) < 13 or len(normalized) > 19:
            errors.append(ErrorItem("INVALID_LENGTH", f"Card number length must be 13-19, got {len(normalized)}"))
            return ValidationResult(False, errors)
        if not CardValidator._luhn(normalized):
            errors.append(ErrorItem("INVALID_CHECKSUM", "Card number failed Luhn check"))
            return ValidationResult(False, errors)
        return ValidationResult(True)

    @staticmethod
    def _luhn(number: str) -> bool:
        digits = [int(d) for d in number]
        checksum = 0
        for i, d in enumerate(reversed(digits)):
            if i % 2 == 1:
                d *= 2
                if d > 9:
                    d -= 9
            checksum += d
        return checksum % 10 == 0
