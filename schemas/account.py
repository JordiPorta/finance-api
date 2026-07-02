from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from models.account import AccountType


class AccountCreate(BaseModel):
    name: str
    type: AccountType = AccountType.checking
    currency: str = "EUR"
    balance: float = 0.0


class AccountUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[AccountType] = None
    currency: Optional[str] = None
    balance: Optional[float] = None


class AccountRead(BaseModel):
    id: int
    name: str
    type: AccountType
    currency: str
    balance: float
    created_at: datetime
