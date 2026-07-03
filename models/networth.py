from datetime import date as date_type, datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class NetWorth(SQLModel, table=True):
    """A point-in-time snapshot of a user's net worth."""

    __tablename__ = "networth"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    date: date_type = Field(index=True)
    liquid_cash: float = Field(default=0.0)
    investments_value: float = Field(default=0.0)
    total_assets: float = Field(default=0.0)
    total_liabilities: float = Field(default=0.0)
    net: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
