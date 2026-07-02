from datetime import date as date_type, datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class TransactionType(str, Enum):
    income = "income"
    expense = "expense"
    transfer = "transfer"


class Transaction(SQLModel, table=True):
    __tablename__ = "transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    account_id: int = Field(foreign_key="accounts.id", index=True)
    category_id: Optional[int] = Field(
        default=None, foreign_key="categories.id", index=True
    )
    type: TransactionType = Field(default=TransactionType.expense)
    amount: float
    description: Optional[str] = None
    date: date_type = Field(index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
