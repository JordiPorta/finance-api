from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class AccountType(str, Enum):
    checking = "checking"
    savings = "savings"
    cash = "cash"
    credit = "credit"
    investment = "investment"
    other = "other"


class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str
    type: AccountType = Field(default=AccountType.checking)
    currency: str = Field(default="EUR", max_length=3)
    balance: float = Field(default=0.0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
