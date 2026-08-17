from dataclasses import dataclass, field
from typing import List

@dataclass
class ErrorItem:
    code: str
    message: str

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[ErrorItem] = field(default_factory=list)
