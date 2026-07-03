from typing import Optional

from pydantic import BaseModel

from models.category import CategoryType


class CategoryCreate(BaseModel):
    name: str
    type: CategoryType
    color: Optional[str] = None


class CategoryRead(BaseModel):
    id: int
    user_id: int
    name: str
    type: CategoryType
    color: Optional[str]
