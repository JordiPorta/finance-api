from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class InvestmentType(str, Enum):
    stock = "stock"
    etf = "etf"
    crypto = "crypto"
    bond = "bond"
    fund = "fund"
    other = "other"


class Investment(SQLModel, table=True):
    """A holding position for a given symbol, updated on buy/sell operations."""

    __tablename__ = "investments"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    symbol: str = Field(index=True)
    name: Optional[str] = None
    type: InvestmentType = Field(default=InvestmentType.stock)
    quantity: float = Field(default=0.0)
    # Average purchase price per unit for the currently held quantity.
    avg_price: float = Field(default=0.0)
    current_price: Optional[float] = None
    currency: str = Field(default="EUR", max_length=3)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class InvestmentTradeType(str, Enum):
    buy = "buy"
    sell = "sell"


class InvestmentTrade(SQLModel, table=True):
    """Immutable log of every buy/sell operation, used for history."""

    __tablename__ = "investment_trades"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    investment_id: int = Field(foreign_key="investments.id", index=True)
    symbol: str = Field(index=True)
    side: InvestmentTradeType
    quantity: float
    price: float
    # Realized profit/loss for a sell operation (0 for buys).
    realized_pnl: float = Field(default=0.0)
    executed_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
