"""Generación de movimientos a partir de gastos fijos (`RecurringExpense`).

No hay scheduler/cron en esta app -- "automático" se resuelve sincronizando de forma perezosa
e idempotente (`sync_recurring_expenses`) cada vez que el frontend carga la app (ver
`POST /recurring-expenses/sync`), no con un job real corriendo en el tiempo.

`RecurringExpense.last_generated_on` (no un exists-check contra `transactions`) es la fuente de
verdad de qué período sigue: avanza siempre que se genera uno, sin importar si el usuario borra
esa transacción después -- así un borrado no "resucita" en el próximo sync.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RecurringExpense, Transaction, TransactionType, User
from app.services.balances import apply_transaction_balance_effect
from app.services.billing_cycle import _safe_day


def _add_month(year: int, month: int) -> tuple[int, int]:
    month += 1
    if month > 12:
        month, year = 1, year + 1
    return year, month


def _due_dates(expense: RecurringExpense, as_of: date) -> list[date]:
    """Períodos (uno por mes) pendientes de generar entre el último generado (o `start_date`
    si nunca se generó ninguno) y `as_of` inclusive -- solo si `as_of` ya alcanzó
    `day_of_month` ese mes; si no, el último período incluido es el mes anterior."""
    if expense.last_generated_on is not None:
        year, month = _add_month(
            expense.last_generated_on.year, expense.last_generated_on.month
        )
    else:
        year, month = expense.start_date.year, expense.start_date.month
    if (year, month) < (expense.start_date.year, expense.start_date.month):
        year, month = expense.start_date.year, expense.start_date.month

    last_year, last_month = as_of.year, as_of.month
    # Comparar contra el día recortado de *este* mes, no el crudo -- si no, un day_of_month=31
    # nunca se consideraría vencido en febrero (28/29 < 31) y se correría un mes de más.
    if as_of.day < _safe_day(last_year, last_month, expense.day_of_month):
        last_month -= 1
        if last_month < 1:
            last_month, last_year = 12, last_year - 1

    dates: list[date] = []
    while (year, month) <= (last_year, last_month):
        dates.append(date(year, month, _safe_day(year, month, expense.day_of_month)))
        year, month = _add_month(year, month)
    return dates


async def sync_recurring_expenses(session: AsyncSession, user: User) -> list[Transaction]:
    """Genera todas las transacciones vencidas de los gastos fijos activos del usuario y
    avanza `last_generated_on` de cada uno. Idempotente: llamarla sin períodos pendientes no
    genera nada."""
    expenses = (
        (
            await session.execute(
                select(RecurringExpense).where(
                    RecurringExpense.user_id == user.id,
                    RecurringExpense.is_active.is_(True),
                )
            )
        )
        .scalars()
        .all()
    )

    generated: list[Transaction] = []
    today = date.today()
    for expense in expenses:
        for period_date in _due_dates(expense, today):
            transaction = Transaction(
                user_id=user.id,
                type=TransactionType.EXPENSE,
                account_id=expense.account_id,
                category_id=expense.category_id,
                recurring_expense_id=expense.id,
                amount=expense.amount,
                currency=expense.currency,
                date=period_date,
                description=expense.description,
            )
            session.add(transaction)
            await session.flush()
            await apply_transaction_balance_effect(session, transaction, card=None)
            expense.last_generated_on = period_date
            generated.append(transaction)

    await session.commit()
    return generated
