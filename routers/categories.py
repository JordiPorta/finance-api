from fastapi import APIRouter, HTTPException, status
from sqlmodel import select

from core.deps import CurrentUser, SessionDep
from models.category import Category
from schemas.category import CategoryCreate, CategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=list[CategoryRead])
def list_categories(current_user: CurrentUser, session: SessionDep):
    return session.exec(
        select(Category).where(Category.user_id == current_user.id)
    ).all()


@router.post("/", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate, current_user: CurrentUser, session: SessionDep
):
    category = Category(user_id=current_user.id, **data.model_dump())
    session.add(category)
    session.commit()
    session.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, current_user: CurrentUser, session: SessionDep):
    category = session.get(Category, category_id)
    if category is None or category.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    session.delete(category)
    session.commit()
