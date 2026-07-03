from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class AccountType(str, Enum):
    bank = "bank"
    broker = "broker"
    crypto = "crypto"
    cash = "cash"
    pension = "pension"


class Account(SQLModel, table=True):
    __tablename__ = "accounts"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str
    type: AccountType
    currency: str = Field(default="EUR", max_length=3)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
