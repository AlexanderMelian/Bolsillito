from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models import AccountType


class AccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    type: AccountType
    currency: str = "ARS"
    balance: Decimal = Decimal("0.00")


class AccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    type: AccountType | None = None
    currency: str | None = None
    balance: Decimal | None = None


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: AccountType
    currency: str
    balance: Decimal
    is_archived: bool
