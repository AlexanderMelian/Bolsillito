from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class InstallmentPlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    card_id: int
    category_id: int | None = None
    description: str
    purchase_date: date
    total_amount: Decimal
    total_installments: int

    @field_validator("total_installments")
    @classmethod
    def check_positive_installments(cls, value: int) -> int:
        if value < 1:
            raise ValueError("total_installments debe ser al menos 1")
        return value

    @field_validator("total_amount")
    @classmethod
    def check_positive_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("total_amount debe ser mayor a 0")
        return value


class InstallmentItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    number: int
    amount: Decimal
    statement_id: int | None


class InstallmentPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    category_id: int | None
    description: str
    purchase_date: date
    total_amount: Decimal
    total_installments: int
    items: list[InstallmentItemRead]
