from pydantic import BaseModel, Field

class CardRequest(BaseModel):
    card_number: str = Field(..., min_length=1)
