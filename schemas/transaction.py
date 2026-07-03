from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from models.transaction import TransactionType


class TransactionCreate(BaseModel):
    account_id: int
    category_id: Optional[int] = None
    amount: float
    type: TransactionType
    description: Optional[str] = None
    date: date
    is_recurring: bool = False


class TransactionUpdate(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    amount: Optional[float] = None
    type: Optional[TransactionType] = None
    description: Optional[str] = None
    date: Optional[date] = None
    is_recurring: Optional[bool] = None


class TransactionRead(BaseModel):
    id: int
    account_id: int
    category_id: Optional[int]
    amount: float
    type: TransactionType
    description: Optional[str]
    date: date
    is_recurring: bool
    created_at: datetime
