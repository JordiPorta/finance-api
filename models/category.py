from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class CategoryType(str, Enum):
    income = "income"
    expense = "expense"


class Category(SQLModel, table=True):
    __tablename__ = "categories"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", index=True)
    name: str
    type: CategoryType
    color: Optional[str] = Field(default=None, max_length=7)
