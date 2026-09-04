from decimal import Decimal

from pydantic import BaseModel, ConfigDict, model_validator

from app.models import CardType


def _validate_credit_card_cycle(
    card_type: CardType, closing_day: int | None, payment_day: int | None
) -> None:
    if card_type == CardType.CREDIT and (closing_day is None or payment_day is None):
        raise ValueError(
            "closing_day y payment_day son obligatorios para tarjetas de crédito (type=credit)"
        )


class CardCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: int
    payment_account_id: int | None = None
    name: str
    type: CardType
    credit_limit: Decimal | None = None
    closing_day: int | None = None
    payment_day: int | None = None

    @model_validator(mode="after")
    def check_credit_card_has_cycle(self) -> "CardCreate":
        _validate_credit_card_cycle(self.type, self.closing_day, self.payment_day)
        return self


class CardUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    payment_account_id: int | None = None
    name: str | None = None
    type: CardType | None = None
    credit_limit: Decimal | None = None
    closing_day: int | None = None
    payment_day: int | None = None


class CardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    payment_account_id: int | None
    name: str
    type: CardType
    credit_limit: Decimal | None
    closing_day: int | None
    payment_day: int | None
