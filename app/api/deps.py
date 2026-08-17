from app.domain.validation_service import ValidationService

def get_validation_service() -> ValidationService:
    return ValidationService()
