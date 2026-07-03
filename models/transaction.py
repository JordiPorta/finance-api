from datetime import date as date_type, datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class TransactionType(str, Enum):
    income = "income"
    expense = "expense"


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id", index=True)
    category_id: Optional[int] = Field(
        default=None, foreign_key="categories.id", index=True
    )
    amount: float
    type: TransactionType
    description: Optional[str] = None
    date: date_type = Field(index=True)
    is_recurring: bool = Field(default=False)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
