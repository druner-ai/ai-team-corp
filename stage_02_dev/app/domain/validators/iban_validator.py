import re
from app.domain.validators.models import ValidationResult, ErrorItem

class IbanValidator:
    @staticmethod
    def validate(normalized: str) -> ValidationResult:
        errors = []
        if not normalized:
            errors.append(ErrorItem("INVALID_LENGTH", "IBAN is empty"))
            return ValidationResult(False, errors)
        if len(normalized) < 15 or len(normalized) > 34:
            errors.append(ErrorItem("INVALID_LENGTH", f"IBAN length must be 15-34, got {len(normalized)}"))
            return ValidationResult(False, errors)
        if not re.match(r'^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$', normalized):
            errors.append(ErrorItem("INVALID_FORMAT", "Invalid IBAN format"))
            return ValidationResult(False, errors)
        if not IbanValidator._mod97(normalized):
            errors.append(ErrorItem("INVALID_CHECKSUM", "IBAN failed mod-97 check"))
            return ValidationResult(False, errors)
        return ValidationResult(True)

    @staticmethod
    def _mod97(iban: str) -> bool:
        rearranged = iban[4:] + iban[:4]
        numeric = ''.join(str(int(c, 36)) for c in rearranged)
        remainder = 0
        for i in range(0, len(numeric), 7):
            block = numeric[i:i+7]
            remainder = int(str(remainder) + block) % 97
        return remainder == 1
