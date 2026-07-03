from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from core.deps import CurrentUser, SessionDep
from models.account import Account
from models.investment import (
    Asset,
    Investment,
    InvestmentOperation,
    OperationType,
)
from routers.accounts import get_owned_account
from schemas.investment import (
    AssetCreate,
    AssetRead,
    BuyOrder,
    InvestmentPosition,
    InvestmentRead,
    InvestmentSummary,
    SellOrder,
)

router = APIRouter(prefix="/investments", tags=["investments"])


def _get_owned_investment(
    investment_id: int, current_user: CurrentUser, session: SessionDep
) -> Investment:
    """Fetch an investment and verify ownership through its account."""
    investment = session.get(Investment, investment_id)
    if investment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Investment not found"
        )
    account = session.get(Account, investment.account_id)
    if account is None or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Investment not found"
        )
    return investment


def _open_positions(current_user: CurrentUser, session: SessionDep) -> list[Investment]:
    return session.exec(
        select(Investment)
        .join(Account, Account.id == Investment.account_id)
        .where(Account.user_id == current_user.id)
        .where(Investment.closed_at == None)  # noqa: E711
    ).all()


# --- Assets ---------------------------------------------------------------


@router.get("/assets", response_model=list[AssetRead])
def list_assets(current_user: CurrentUser, session: SessionDep):
    return session.exec(select(Asset)).all()


@router.post("/assets", response_model=AssetRead, status_code=status.HTTP_201_CREATED)
def create_asset(data: AssetCreate, current_user: CurrentUser, session: SessionDep):
    existing = session.exec(
        select(Asset).where(Asset.ticker == data.ticker)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset with this ticker already exists",
        )
    asset = Asset(**data.model_dump())
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset


# --- Positions ------------------------------------------------------------


@router.get("/", response_model=list[InvestmentRead])
def list_investments(current_user: CurrentUser, session: SessionDep):
    """Open positions for the current user."""
    return _open_positions(current_user, session)


@router.get("/summary", response_model=InvestmentSummary)
def investments_summary(current_user: CurrentUser, session: SessionDep):
    positions = _open_positions(current_user, session)

    enriched: list[InvestmentPosition] = []
    total_invested = 0.0
    for inv in positions:
        asset = session.get(Asset, inv.asset_id)
        invested = inv.shares * inv.avg_buy_price
        total_invested += invested
        enriched.append(
            InvestmentPosition(
                id=inv.id,
                account_id=inv.account_id,
                asset=AssetRead.model_validate(asset, from_attributes=True),
                shares=inv.shares,
                avg_buy_price=inv.avg_buy_price,
                invested=invested,
                currency=inv.currency,
            )
        )

    return InvestmentSummary(
        total_invested=total_invested,
        open_positions=len(enriched),
        positions=enriched,
    )


@router.post("/", response_model=InvestmentRead, status_code=status.HTTP_201_CREATED)
def buy(order: BuyOrder, current_user: CurrentUser, session: SessionDep):
    """Execute a buy: opens a new position or adds to an existing open one,
    recalculating the weighted average buy price."""
    get_owned_account(order.account_id, current_user, session)

    asset = session.get(Asset, order.asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found"
        )
    if order.shares <= 0 or order.price < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shares must be positive and price non-negative",
        )

    investment = session.exec(
        select(Investment)
        .where(Investment.account_id == order.account_id)
        .where(Investment.asset_id == order.asset_id)
        .where(Investment.closed_at == None)  # noqa: E711
    ).first()

    if investment is None:
        investment = Investment(
            account_id=order.account_id,
            asset_id=order.asset_id,
            shares=order.shares,
            avg_buy_price=order.price,
            currency=order.currency,
        )
    else:
        # Weighted average: (old_shares * old_avg + new_shares * price) / total
        total_shares = investment.shares + order.shares
        investment.avg_buy_price = (
            investment.shares * investment.avg_buy_price
            + order.shares * order.price
        ) / total_shares
        investment.shares = total_shares

    session.add(investment)
    session.commit()
    session.refresh(investment)

    operation = InvestmentOperation(
        investment_id=investment.id,
        type=OperationType.buy,
        shares=order.shares,
        price=order.price,
        fees=order.fees,
        date=order.date,
    )
    session.add(operation)
    session.commit()
    session.refresh(investment)
    return investment


@router.post("/{investment_id}/sell", response_model=InvestmentRead)
def sell(
    investment_id: int,
    order: SellOrder,
    current_user: CurrentUser,
    session: SessionDep,
):
    """Execute a sell: reduces shares; closes the position when it hits zero."""
    investment = _get_owned_investment(investment_id, current_user, session)

    if investment.closed_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position is already closed",
        )
    if order.shares <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Shares must be positive",
        )
    if order.shares > investment.shares:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot sell more shares than currently held",
        )

    investment.shares -= order.shares
    if investment.shares == 0:
        investment.closed_at = datetime.now(timezone.utc)

    operation = InvestmentOperation(
        investment_id=investment.id,
        type=OperationType.sell,
        shares=order.shares,
        price=order.price,
        fees=order.fees,
        date=order.date,
    )
    session.add(investment)
    session.add(operation)
    session.commit()
    session.refresh(investment)
    return investment


@router.get("/{investment_id}/history")
def investment_history(
    investment_id: int, current_user: CurrentUser, session: SessionDep
):
    """All buy/sell operations for a position, oldest first."""
    _get_owned_investment(investment_id, current_user, session)
    return session.exec(
        select(InvestmentOperation)
        .where(InvestmentOperation.investment_id == investment_id)
        .order_by(InvestmentOperation.date)
    ).all()
