from app.utils.normalizer import Normalizer
from app.utils.masker import Masker
from app.utils.hasher import Hasher
from app.domain.validators.card_validator import CardValidator
from app.domain.validators.iban_validator import IbanValidator
from app.domain.validators.account_validator import AccountValidator
from app.domain.validators.models import ValidationResult
from app.domain.exceptions import InvalidFormatError

class ValidationService:
    def validate_card(self, raw: str) -> dict:
        normalized = Normalizer.normalize(raw)
        if not normalized:
            raise InvalidFormatError("INVALID_FORMAT", "Card number is empty after normalization")
        result = CardValidator.validate(normalized)
        if not result.is_valid:
            for e in result.errors:
                if e.code == "INVALID_FORMAT":
                    raise InvalidFormatError(e.code, e.message)
        return self._build_response(raw, normalized, "card", result)

    def validate_iban(self, raw: str) -> dict:
        normalized = Normalizer.normalize(raw)
        if not normalized:
            raise InvalidFormatError("INVALID_FORMAT", "IBAN is empty after normalization")
        result = IbanValidator.validate(normalized)
        if not result.is_valid:
            for e in result.errors:
                if e.code == "INVALID_FORMAT":
                    raise InvalidFormatError(e.code, e.message)
        return self._build_response(raw, normalized, "iban", result)

    def validate_account(self, bik: str, account: str) -> dict:
        bik_norm = Normalizer.normalize(bik)
        acc_norm = Normalizer.normalize(account)
        if not bik_norm or not acc_norm:
            raise InvalidFormatError("INVALID_FORMAT", "BIK or account is empty after normalization")
        result = AccountValidator.validate(bik_norm, acc_norm)
        if not result.is_valid:
            for e in result.errors:
                if e.code == "INVALID_FORMAT":
                    raise InvalidFormatError(e.code, e.message)
        original = f"{bik}/{account}"
        normalized = f"{bik_norm}|{acc_norm}"
        return self._build_response(original, normalized, "account", result)

    def _build_response(self, original: str, normalized: str, req_type: str, result: ValidationResult) -> dict:
        mask = Masker.mask(normalized)
        hash_val = Hasher.hash(normalized)
        return {
            "original": original,
            "normalized": normalized,
            "is_valid": result.is_valid,
            "type": req_type,
            "mask": mask,
            "hash": hash_val,
            "errors": [{"code": e.code, "message": e.message} for e in result.errors]
        }
