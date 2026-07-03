from datetime import date

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from core.deps import CurrentUser, SessionDep
from models.account import Account
from models.category import Category
from models.investment import Investment
from models.networth import NetWorth
from models.transaction import Transaction, TransactionType

router = APIRouter(prefix="/stats", tags=["stats"])


def _parse_period(period: str) -> tuple[date, date]:
    """Turn 'YYYY-MM' into (first_day, last_day) of that month."""
    try:
        year, month = map(int, period.split("-"))
        start = date(year, month, 1)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period, expected YYYY-MM",
        )
    if month == 12:
        end = date(year + 1, 1, 1)
    else:
        end = date(year, month + 1, 1)
    return start, end


def _user_transactions_query(user_id: int):
    return (
        select(Transaction)
        .join(Account, Account.id == Transaction.account_id)
        .where(Account.user_id == user_id)
    )


@router.get("/cashflow")
def cashflow(
    current_user: CurrentUser,
    session: SessionDep,
    period: str = Query(..., description="Month in YYYY-MM format"),
):
    """Income, expenses and net cashflow for a given month."""
    start, end = _parse_period(period)

    transactions = session.exec(
        _user_transactions_query(current_user.id)
        .where(Transaction.date >= start)
        .where(Transaction.date < end)
    ).all()

    income = sum(t.amount for t in transactions if t.type == TransactionType.income)
    expenses = sum(t.amount for t in transactions if t.type == TransactionType.expense)

    return {
        "period": period,
        "income": income,
        "expenses": expenses,
        "net": income - expenses,
    }


@router.get("/expenses/by-category")
def expenses_by_category(
    current_user: CurrentUser,
    session: SessionDep,
    period: str | None = Query(default=None, description="Optional month YYYY-MM"),
):
    """Total expenses grouped by category (optionally limited to one month)."""
    query = _user_transactions_query(current_user.id).where(
        Transaction.type == TransactionType.expense
    )
    if period is not None:
        start, end = _parse_period(period)
        query = query.where(Transaction.date >= start).where(Transaction.date < end)

    transactions = session.exec(query).all()

    totals: dict[int | None, float] = {}
    for t in transactions:
        totals[t.category_id] = totals.get(t.category_id, 0.0) + t.amount

    result = []
    for category_id, total in sorted(totals.items(), key=lambda x: -x[1]):
        category = session.get(Category, category_id) if category_id else None
        result.append(
            {
                "category_id": category_id,
                "category": category.name if category else "Uncategorized",
                "color": category.color if category else None,
                "total": total,
            }
        )
    return result


@router.get("/networth/history")
def networth_history(current_user: CurrentUser, session: SessionDep):
    """All net worth snapshots for the user, oldest first."""
    return session.exec(
        select(NetWorth)
        .where(NetWorth.user_id == current_user.id)
        .order_by(NetWorth.date)
    ).all()


@router.post("/networth/snapshot", status_code=status.HTTP_201_CREATED)
def networth_snapshot(current_user: CurrentUser, session: SessionDep):
    """Compute and store a net worth snapshot as of today.

    liquid_cash = sum of income - expenses across all the user's accounts.
    investments_value = sum of shares * avg_buy_price of open positions.
    """
    transactions = session.exec(_user_transactions_query(current_user.id)).all()
    liquid_cash = sum(
        t.amount if t.type == TransactionType.income else -t.amount
        for t in transactions
    )

    investments = session.exec(
        select(Investment)
        .join(Account, Account.id == Investment.account_id)
        .where(Account.user_id == current_user.id)
        .where(Investment.closed_at == None)  # noqa: E711
    ).all()
    investments_value = sum(i.shares * i.avg_buy_price for i in investments)

    total_assets = liquid_cash + investments_value
    total_liabilities = 0.0

    snapshot = NetWorth(
        user_id=current_user.id,
        date=date.today(),
        liquid_cash=liquid_cash,
        investments_value=investments_value,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        net=total_assets - total_liabilities,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot
