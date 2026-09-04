from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ExchangeRateCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    from_currency: str
    to_currency: str
    rate: Decimal
    date: date_type


class ExchangeRateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_currency: str
    to_currency: str
    rate: Decimal
    date: date_type
