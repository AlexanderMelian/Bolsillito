from pydantic import BaseModel, ConfigDict

from app.models import TransactionType


class CategoryCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    kind: TransactionType
    icon: str | None = None


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    kind: TransactionType | None = None
    icon: str | None = None


class CategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    kind: TransactionType
    icon: str | None
