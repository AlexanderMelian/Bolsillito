from datetime import date as date_type
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, field_validator

from app.models import AssetType, InvestmentTxType
from app.schemas.dashboard import UnconvertedAmount


class InvestmentTransactionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    account_id: int | None = None
    type: InvestmentTxType
    quantity: Decimal
    price: Decimal
    fee: Decimal = Decimal("0.00")
    date: date_type

    @field_validator("quantity")
    @classmethod
    def check_quantity_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("quantity debe ser mayor a 0")
        return value

    @field_validator("price")
    @classmethod
    def check_price_positive(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError("price debe ser mayor a 0")
        return value

    @field_validator("fee")
    @classmethod
    def check_fee_not_negative(cls, value: Decimal) -> Decimal:
        if value < 0:
            raise ValueError("fee no puede ser negativo")
        return value


class InvestmentTransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    account_id: int | None
    type: InvestmentTxType
    quantity: Decimal
    price: Decimal
    fee: Decimal
    date: date_type


class AssetPosition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: int
    ticker: str
    name: str
    type: AssetType
    currency: str
    quantity: Decimal
    avg_cost: Decimal
    total_cost: Decimal
    realized_gain: Decimal


class Portfolio(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_currency: str
    total_cost: Decimal
    total_realized_gain: Decimal
    unconverted: list[UnconvertedAmount]
    positions: list[AssetPosition]
