from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator


class RecurringExpenseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # None: gasto fijo sin cuenta asociada, para el usuario al que solo le importa el total de
    # ingresos/egresos sin llevar detalle de billetera/banco -- no afecta ningún saldo.
    account_id: int | None = None
    category_id: int | None = None
    description: str
    amount: Decimal
    currency: str | None = None
    day_of_month: int
    start_date: date

    @field_validator("amount")
    @classmethod
    def check_positive_amount(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("amount debe ser mayor a 0")
        return value

    @field_validator("day_of_month")
    @classmethod
    def check_day_of_month(cls, value: int) -> int:
        if not 1 <= value <= 31:
            raise ValueError("day_of_month debe estar entre 1 y 31")
        return value


class RecurringExpenseUpdate(BaseModel):
    """`start_date` no se puede editar -- ya ancla los períodos generados hasta ahora
    (`last_generated_on`); cambiarla desincronizaría qué meses se consideran cubiertos."""

    model_config = ConfigDict(extra="forbid")

    account_id: int | None = None
    category_id: int | None = None
    description: str | None = None
    amount: Decimal | None = None
    day_of_month: int | None = None
    is_active: bool | None = None

    @field_validator("amount")
    @classmethod
    def check_positive_amount(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and value <= 0:
            raise ValueError("amount debe ser mayor a 0")
        return value

    @field_validator("day_of_month")
    @classmethod
    def check_day_of_month(cls, value: int | None) -> int | None:
        if value is not None and not 1 <= value <= 31:
            raise ValueError("day_of_month debe estar entre 1 y 31")
        return value


class RecurringExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int | None
    category_id: int | None
    description: str
    amount: Decimal
    currency: str
    day_of_month: int
    start_date: date
    last_generated_on: date | None
    is_active: bool


class RecurringExpenseSyncResult(BaseModel):
    generated_count: int
