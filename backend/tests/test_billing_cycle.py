from datetime import date
from decimal import Decimal

from app.billing_cycle import (
    build_installment_amounts,
    build_installment_closing_dates,
    get_payment_due_date,
    get_statement_closing_date,
)

CLOSING_DAY = 15
PAYMENT_DAY = 25


def test_purchase_on_closing_day_belongs_to_current_cycle():
    assert get_statement_closing_date(date(2026, 3, 15), CLOSING_DAY) == date(2026, 3, 15)


def test_purchase_before_closing_day_belongs_to_current_cycle():
    assert get_statement_closing_date(date(2026, 3, 14), CLOSING_DAY) == date(2026, 3, 15)


def test_purchase_after_closing_day_belongs_to_next_cycle():
    assert get_statement_closing_date(date(2026, 3, 16), CLOSING_DAY) == date(2026, 4, 15)


def test_closing_day_clamped_on_short_months():
    # closing_day=31 no existe en febrero -> se recorta al último día real del mes.
    assert get_statement_closing_date(date(2026, 2, 20), 31) == date(2026, 2, 28)


def test_payment_due_date_same_month_when_payment_day_after_closing_day():
    assert get_payment_due_date(date(2026, 3, 15), PAYMENT_DAY) == date(2026, 3, 25)


def test_payment_due_date_next_month_when_payment_day_before_closing_day():
    assert get_payment_due_date(date(2026, 3, 15), 5) == date(2026, 4, 5)


def test_installment_closing_dates_cross_year_boundary():
    dates = build_installment_closing_dates(date(2026, 12, 20), CLOSING_DAY, 3)
    assert dates == [date(2027, 1, 15), date(2027, 2, 15), date(2027, 3, 15)]


def test_installment_amounts_sum_exactly_to_total_despite_rounding():
    amounts = build_installment_amounts(Decimal("100.00"), 3)
    assert sum(amounts) == Decimal("100.00")
    assert amounts == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
