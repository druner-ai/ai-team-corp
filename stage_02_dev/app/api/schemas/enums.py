from enum import Enum

class ReqType(str, Enum):
    CARD = "card"
    IBAN = "iban"
    ACCOUNT = "account"

class ErrorCode(str, Enum):
    INVALID_CHECKSUM = "INVALID_CHECKSUM"
    INVALID_LENGTH = "INVALID_LENGTH"
    INVALID_FORMAT = "INVALID_FORMAT"
    ROUTE_NOT_FOUND = "ROUTE_NOT_FOUND"
    INTERNAL_ERROR = "INTERNAL_ERROR"
