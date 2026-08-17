from pydantic import BaseModel
from typing import List, Optional, Any

class ErrorItem(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    error: ErrorItem
    detail: Optional[Any] = None

class ValidationResultResponse(BaseModel):
    original: str
    normalized: str
    is_valid: bool
    type: str
    mask: str
    hash: str
    errors: List[ErrorItem]
