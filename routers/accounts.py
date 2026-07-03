from fastapi import APIRouter, HTTPException, status
from sqlmodel import Session, select

from core.deps import CurrentUser, SessionDep
from models.account import Account
from models.user import User
from schemas.account import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


def get_owned_account(account_id: int, user: User, session: Session) -> Account:
    """Fetch an account and verify it belongs to the given user (404 otherwise)."""
    account = session.get(Account, account_id)
    if account is None or account.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Account not found"
        )
    return account


@router.get("/", response_model=list[AccountRead])
def list_accounts(current_user: CurrentUser, session: SessionDep):
    return session.exec(
        select(Account).where(Account.user_id == current_user.id)
    ).all()


@router.post("/", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(data: AccountCreate, current_user: CurrentUser, session: SessionDep):
    account = Account(user_id=current_user.id, **data.model_dump())
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountRead)
def get_account(account_id: int, current_user: CurrentUser, session: SessionDep):
    return get_owned_account(account_id, current_user, session)


@router.put("/{account_id}", response_model=AccountRead)
def update_account(
    account_id: int,
    data: AccountUpdate,
    current_user: CurrentUser,
    session: SessionDep,
):
    account = get_owned_account(account_id, current_user, session)
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(account, key, value)
    session.add(account)
    session.commit()
    session.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: int, current_user: CurrentUser, session: SessionDep):
    account = get_owned_account(account_id, current_user, session)
    session.delete(account)
    session.commit()
