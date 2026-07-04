from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from models.investment import AssetType


class AssetCreate(BaseModel):
    ticker: str
    isin: Optional[str] = None
    name: str
    type: AssetType


class AssetRead(BaseModel):
    id: int
    ticker: str
    isin: Optional[str] = None
    name: str
    type: AssetType
    last_price: Optional[float] = None
    last_price_at: Optional[datetime] = None


class AssetPriceUpdate(BaseModel):
    price: float


class BuyOrder(BaseModel):
    account_id: int
    asset_id: int
    shares: float
    price: float
    amount: Optional[float] = None
    fees: float = 0.0
    note: Optional[str] = None
    date: date
    currency: str = "EUR"


class SellOrder(BaseModel):
    shares: float
    price: float
    amount: Optional[float] = None
    fees: float = 0.0
    note: Optional[str] = None
    date: date


class SplitOrder(BaseModel):
    ratio: float  # 25 means 25:1 (each old share becomes 25)
    date: date
    note: Optional[str] = None


class InvestmentRead(BaseModel):
    id: int
    account_id: int
    asset_id: int
    shares: float
    avg_buy_price: float
    currency: str
    opened_at: datetime
    closed_at: Optional[datetime]


class InvestmentPosition(BaseModel):
    """A position enriched with its asset info and invested value."""

    id: int
    account_id: int
    asset: AssetRead
    shares: float
    avg_buy_price: float
    invested: float
    currency: str


class InvestmentSummary(BaseModel):
    total_invested: float
    open_positions: int
    positions: list[InvestmentPosition]


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
    investment_ids: list[int]


class ProgressPoint(BaseModel):
    """Portfolio state right after an operation: value = cumulative shares x that day's price."""

    date: date
    invested: float
    shares: float
    price: float
    value: float
    return_pct: float
    note: Optional[str] = None


class InvestmentProgress(BaseModel):
    investment_id: int
    asset: AssetRead
    points: list[ProgressPoint]
    total_invested: float
    total_fees: float
    current_value: Optional[float] = None
    current_return_pct: Optional[float] = None
