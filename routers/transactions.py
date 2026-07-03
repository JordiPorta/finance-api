from datetime import date
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, status
from sqlmodel import select

from core.deps import CurrentUser, SessionDep
from models.account import Account
from models.transaction import Transaction, TransactionType
from routers.accounts import get_owned_account
from schemas.transaction import TransactionCreate, TransactionRead, TransactionUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _get_owned_transaction(
    transaction_id: int, current_user: CurrentUser, session: SessionDep
) -> Transaction:
    """Fetch a transaction and verify ownership through its account."""
    transaction = session.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    account = session.get(Account, transaction.account_id)
    if account is None or account.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found"
        )
    return transaction


@router.get("/", response_model=list[TransactionRead])
def list_transactions(
    current_user: CurrentUser,
    session: SessionDep,
    account_id: Optional[int] = Query(default=None),
    category_id: Optional[int] = Query(default=None),
    from_date: Optional[date] = Query(default=None),
    to_date: Optional[date] = Query(default=None),
    type: Optional[TransactionType] = Query(default=None),
):
    query = (
        select(Transaction)
        .join(Account, Account.id == Transaction.account_id)
        .where(Account.user_id == current_user.id)
    )

    if account_id is not None:
        query = query.where(Transaction.account_id == account_id)
    if category_id is not None:
        query = query.where(Transaction.category_id == category_id)
    if from_date is not None:
        query = query.where(Transaction.date >= from_date)
    if to_date is not None:
        query = query.where(Transaction.date <= to_date)
    if type is not None:
        query = query.where(Transaction.type == type)

    query = query.order_by(Transaction.date.desc())
    return session.exec(query).all()


@router.post("/", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
def create_transaction(
    data: TransactionCreate, current_user: CurrentUser, session: SessionDep
):
    # Ownership check: the target account must belong to the current user.
    get_owned_account(data.account_id, current_user, session)

    transaction = Transaction(**data.model_dump())
    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: int, current_user: CurrentUser, session: SessionDep
):
    return _get_owned_transaction(transaction_id, current_user, session)


@router.put("/{transaction_id}", response_model=TransactionRead)
def update_transaction(
    transaction_id: int,
    data: TransactionUpdate,
    current_user: CurrentUser,
    session: SessionDep,
):
    transaction = _get_owned_transaction(transaction_id, current_user, session)

    updates = data.model_dump(exclude_unset=True)
    # If moving to another account, that account must also belong to the user.
    if "account_id" in updates and updates["account_id"] != transaction.account_id:
        get_owned_account(updates["account_id"], current_user, session)

    for key, value in updates.items():
        setattr(transaction, key, value)

    session.add(transaction)
    session.commit()
    session.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: int, current_user: CurrentUser, session: SessionDep
):
    transaction = _get_owned_transaction(transaction_id, current_user, session)
    session.delete(transaction)
    session.commit()
