from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from models.transaction import TransactionType


class TransactionCreate(BaseModel):
    account_id: int
    category_id: Optional[int] = None
    type: TransactionType = TransactionType.expense
    amount: float
    description: Optional[str] = None
    date: date


class TransactionUpdate(BaseModel):
    account_id: Optional[int] = None
    category_id: Optional[int] = None
    type: Optional[TransactionType] = None
    amount: Optional[float] = None
    description: Optional[str] = None
    date: Optional[date] = None


class TransactionRead(BaseModel):
    id: int
    account_id: int
    category_id: Optional[int]
    type: TransactionType
    amount: float
    description: Optional[str]
    date: date
    created_at: datetime
