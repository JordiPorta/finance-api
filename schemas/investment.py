from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from models.investment import InvestmentType, InvestmentTradeType


class InvestmentBuy(BaseModel):
    symbol: str
    quantity: float
    price: float
    name: Optional[str] = None
    type: InvestmentType = InvestmentType.stock
    currency: str = "EUR"


class InvestmentSell(BaseModel):
    symbol: str
    quantity: float
    price: float


class PriceUpdate(BaseModel):
    current_price: float


class InvestmentRead(BaseModel):
    id: int
    symbol: str
    name: Optional[str]
    type: InvestmentType
    quantity: float
    avg_price: float
    current_price: Optional[float]
    currency: str
    created_at: datetime
    updated_at: datetime


class InvestmentTradeRead(BaseModel):
    id: int
    investment_id: int
    symbol: str
    side: InvestmentTradeType
    quantity: float
    price: float
    realized_pnl: float
    executed_at: datetime


class InvestmentSummary(BaseModel):
    total_invested: float
    current_value: float
    unrealized_pnl: float
    realized_pnl: float
    positions: list[InvestmentRead]
