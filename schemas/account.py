from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from models.account import AccountType


class AccountCreate(BaseModel):
    name: str
    type: AccountType
    currency: str = "EUR"


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[AccountType] = None
    currency: Optional[str] = None


class AccountRead(BaseModel):
    id: int
    user_id: int
    name: str
    type: AccountType
    currency: str
    created_at: datetime
