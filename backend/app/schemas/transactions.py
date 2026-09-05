from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator

from app.models import TransactionType


class TransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: TransactionType
    account_id: int
    destination_account_id: int | None = None
    card_id: int | None = None
    category_id: int | None = None
    amount: Decimal
    currency: str | None = None
    date: date_type
    description: str | None = None

    @model_validator(mode="after")
    def check_shape(self) -> "TransactionCreate":
        if self.type == TransactionType.TRANSFER:
            if self.card_id is not None:
                raise ValueError("Una transferencia no puede tener card_id")
            if self.destination_account_id is None:
                raise ValueError("Una transferencia requiere destination_account_id")
            if self.destination_account_id == self.account_id:
                raise ValueError("La cuenta de origen y destino no pueden ser la misma")
        else:
            if self.destination_account_id is not None:
                raise ValueError("destination_account_id solo aplica a transferencias")
            if self.card_id is not None and self.type != TransactionType.EXPENSE:
                raise ValueError("card_id solo aplica a gastos (type=expense)")
        return self


class TransactionUpdate(BaseModel):
    """Solo se puede editar metadata -- cambiar `amount`/`account_id`/`type` requiere revertir
    y recrear el movimiento (DELETE + POST) para no desincronizar el saldo ya aplicado."""

    model_config = ConfigDict(extra="forbid")

    category_id: int | None = None
    date: date_type | None = None
    description: str | None = None


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: TransactionType
    # Nullable porque una instancia generada por un RecurringExpense sin cuenta no tiene una --
    # la carga manual (TransactionCreate.account_id) sigue exigiéndola, esto no cambia eso.
    account_id: int | None
    destination_account_id: int | None
    card_id: int | None
    category_id: int | None
    installment_plan_id: int | None
    recurring_expense_id: int | None
    amount: Decimal
    currency: str
    date: date_type
    description: str | None
