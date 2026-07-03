from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel

from models.investment import AssetType


class AssetCreate(BaseModel):
    ticker: str
    name: str
    type: AssetType


class AssetRead(BaseModel):
    id: int
    ticker: str
    name: str
    type: AssetType


class BuyOrder(BaseModel):
    account_id: int
    asset_id: int
    shares: float
    price: float
    fees: float = 0.0
    date: date
    currency: str = "EUR"


class SellOrder(BaseModel):
    shares: float
    price: float
    fees: float = 0.0
    date: date


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
