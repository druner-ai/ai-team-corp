from abc import ABC, abstractmethod
from app.domain.validators.models import ValidationResult

class BaseValidator(ABC):
    @abstractmethod
    def validate(self, *args) -> ValidationResult:
        pass
