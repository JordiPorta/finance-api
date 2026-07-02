from datetime import date as date_type, datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class NetWorthSnapshot(SQLModel, table=True):
    """A point-in-time snapshot of a user's total net worth."""

    __tablename__ = "networth_snapshots"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    date: date_type = Field(index=True)
    cash_total: float = Field(default=0.0)
    investments_total: float = Field(default=0.0)
    net_worth: float = Field(default=0.0)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
