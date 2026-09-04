from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models import StatementStatus


class CardStatementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    card_id: int
    closing_date: date
    payment_due_date: date
    status: StatementStatus
    total_amount: Decimal
    payment_transaction_id: int | None


class StatementPaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_date: date
