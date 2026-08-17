from pydantic import BaseModel, Field

class AccountRequest(BaseModel):
    bik: str = Field(..., min_length=1)
    account: str = Field(..., min_length=1)
