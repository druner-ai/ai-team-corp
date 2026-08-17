from app.domain.validators.models import ValidationResult, ErrorItem

class AccountValidator:
    @staticmethod
    def validate(bik: str, account: str) -> ValidationResult:
        errors = []
        if not bik or not bik.isdigit() or len(bik) != 9:
            errors.append(ErrorItem("INVALID_FORMAT", "BIK must be 9 digits"))
            return ValidationResult(False, errors)
        if not account:
            errors.append(ErrorItem("INVALID_LENGTH", "Account number is empty"))
            return ValidationResult(False, errors)
        if not account.isdigit():
            errors.append(ErrorItem("INVALID_FORMAT", "Account number must contain only digits"))
            return ValidationResult(False, errors)
        if len(account) not in (20, 28):
            errors.append(ErrorItem("INVALID_LENGTH", f"Account number length must be 20 or 28, got {len(account)}"))
            return ValidationResult(False, errors)
        if not AccountValidator._validate_checksum(bik, account):
            errors.append(ErrorItem("INVALID_CHECKSUM", "Account number failed checksum validation"))
            return ValidationResult(False, errors)
        return ValidationResult(True)

    @staticmethod
    def _validate_checksum(bik: str, account: str) -> bool:
        bik_tail = bik[-3:]
        account_list = list(account)
        account_list[8] = '0'
        account_zeroed = ''.join(account_list)
        combined = bik_tail + account_zeroed
        weights = [7, 1, 3] * (len(combined) // 3 + 1)
        weights = weights[:len(combined)]
        total = sum(int(d) * w for d, w in zip(combined, weights))
        check_digit = (10 - (total % 10)) % 10
        original_check = int(account[8])
        return check_digit == original_check
