from pydantic import BaseModel, Field

class IbanRequest(BaseModel):
    iban: str = Field(..., min_length=1)
