from fastapi import APIRouter, Depends
from app.api.schemas.card import CardRequest
from app.api.schemas.common import ValidationResultResponse
from app.api.deps import get_validation_service
from app.domain.validation_service import ValidationService
from app.domain.exceptions import InvalidFormatError
from fastapi.responses import JSONResponse

router = APIRouter()

@router.post("/validate/card", response_model=ValidationResultResponse)
async def validate_card(request: CardRequest, service: ValidationService = Depends(get_validation_service)):
    try:
        result = service.validate_card(request.card_number)
        return result
    except InvalidFormatError as e:
        return JSONResponse(status_code=400, content={"error": {"code": e.code, "message": e.message}})
