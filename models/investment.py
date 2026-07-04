from datetime import date as date_type, datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class AssetType(str, Enum):
    stock = "stock"
    etf = "etf"
    crypto = "crypto"
    fund = "fund"


class OperationType(str, Enum):
    buy = "buy"
    sell = "sell"
    # Stock split: `shares` holds the ratio (25 for a 25:1 split), price/amount unused.
    split = "split"


class Asset(SQLModel, table=True):
    __tablename__ = "assets"

    id: Optional[int] = Field(default=None, primary_key=True)
    ticker: str = Field(unique=True, index=True)
    isin: Optional[str] = Field(default=None, unique=True, index=True)
    name: str
    type: AssetType
    last_price: Optional[float] = None
    last_price_at: Optional[datetime] = None


class Investment(SQLModel, table=True):
    """An open (or closed) position of an asset held in an account."""

    __tablename__ = "investments"

    id: Optional[int] = Field(default=None, primary_key=True)
    account_id: int = Field(foreign_key="accounts.id", index=True)
    asset_id: int = Field(foreign_key="assets.id", index=True)
    shares: float = Field(default=0.0)
    avg_buy_price: float = Field(default=0.0)
    currency: str = Field(default="EUR", max_length=3)
    opened_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None


class InvestmentOperation(SQLModel, table=True):
    """Immutable log of every buy/sell executed on an investment."""

    __tablename__ = "investment_operations"

    id: Optional[int] = Field(default=None, primary_key=True)
    investment_id: int = Field(foreign_key="investments.id", index=True)
    type: OperationType
    shares: float
    price: float
    # Exact cash moved (buy cost / sell proceeds); shares * price may drift by rounding.
    amount: Optional[float] = None
    fees: float = Field(default=0.0)
    note: Optional[str] = None
    date: date_type = Field(index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
