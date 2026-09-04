from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class UnconvertedAmount(BaseModel):
    model_config = ConfigDict(extra="forbid")

    currency: str
    amount: Decimal


class DashboardSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_currency: str
    month: str
    total_balance: Decimal
    month_income: Decimal
    month_expenses: Decimal
    unconverted_balances: list[UnconvertedAmount]


class CategorySpending(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: int | None
    category_name: str
    icon: str | None
    total: Decimal


class CashFlowMonth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    month: str
    committed_amount: Decimal


class CashFlowProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reference_currency: str
    projection: list[CashFlowMonth]
