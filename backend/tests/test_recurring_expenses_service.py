from datetime import date

from app.models import RecurringExpense
from app.services.recurring_expenses import _add_month, _due_dates


def _expense(**overrides) -> RecurringExpense:
    defaults = {
        "day_of_month": 5,
        "start_date": date(2026, 1, 5),
        "last_generated_on": None,
    }
    return RecurringExpense(**{**defaults, **overrides})


def test_add_month_wraps_to_next_year():
    assert _add_month(2026, 12) == (2027, 1)


def test_add_month_within_same_year():
    assert _add_month(2026, 3) == (2026, 4)


def test_due_dates_never_generated_includes_start_month_if_already_due():
    expense = _expense(start_date=date(2026, 1, 5))
    assert _due_dates(expense, date(2026, 1, 5)) == [date(2026, 1, 5)]


def test_due_dates_never_generated_excludes_start_month_if_not_yet_due():
    expense = _expense(start_date=date(2026, 1, 10), day_of_month=10)
    assert _due_dates(expense, date(2026, 1, 5)) == []


def test_due_dates_catches_up_several_past_months():
    expense = _expense(start_date=date(2025, 11, 5))
    assert _due_dates(expense, date(2026, 2, 5)) == [
        date(2025, 11, 5), date(2025, 12, 5), date(2026, 1, 5), date(2026, 2, 5),
    ]


def test_due_dates_continues_from_last_generated_on():
    expense = _expense(start_date=date(2026, 1, 5), last_generated_on=date(2026, 1, 5))
    assert _due_dates(expense, date(2026, 3, 5)) == [date(2026, 2, 5), date(2026, 3, 5)]


def test_due_dates_is_empty_when_up_to_date():
    expense = _expense(start_date=date(2026, 1, 5), last_generated_on=date(2026, 3, 5))
    assert _due_dates(expense, date(2026, 3, 5)) == []


def test_due_dates_clamps_day_31_in_february():
    expense = _expense(day_of_month=31, start_date=date(2026, 1, 31))
    assert _due_dates(expense, date(2026, 2, 28)) == [date(2026, 1, 31), date(2026, 2, 28)]


def test_due_dates_crosses_year_boundary():
    expense = _expense(start_date=date(2025, 12, 5), last_generated_on=date(2025, 12, 5))
    assert _due_dates(expense, date(2026, 1, 5)) == [date(2026, 1, 5)]
