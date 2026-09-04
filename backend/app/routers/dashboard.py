import calendar
from datetime import date as date_type
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session
from app.models import (
    Account, Card, CardStatement, Category, StatementStatus, Transaction, TransactionType, User,
)
from app.schemas.dashboard import (
    CashFlowMonth, CashFlowProjection, CategorySpending, DashboardSummary, UnconvertedAmount,
)
from app.services.auth import get_current_user
from app.services.card_statements import compute_statement_totals
from app.services.exchange_rates import convert

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def _month_bounds(month: str | None) -> tuple[date_type, date_type, str]:
    if month is None:
        today = date_type.today()
        year, month_num = today.year, today.month
    else:
        try:
            year_str, month_str = month.split("-")
            year, month_num = int(year_str), int(month_str)
            if not 1 <= month_num <= 12:
                raise ValueError
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="month debe tener el formato YYYY-MM",
            ) from exc
    last_day = calendar.monthrange(year, month_num)[1]
    return date_type(year, month_num, 1), date_type(year, month_num, last_day), f"{year:04d}-{month_num:02d}"


def _statement_payment_transaction_ids(user_id: int) -> Select:
    """Subquery: ids de Transaction que son el pago de un resumen. Se excluyen de los reportes
    de ingreso/gasto porque ya se contaron como gasto en el momento de la compra -- si no, un
    pago de resumen se contaría dos veces (una al comprar, otra al pagar)."""
    return select(CardStatement.payment_transaction_id).where(
        CardStatement.payment_transaction_id.is_not(None), CardStatement.user_id == user_id
    )


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(
    month: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> DashboardSummary:
    reference_currency = get_settings().default_currency
    start, end, month_label = _month_bounds(month)
    today = date_type.today()

    accounts = (
        await session.execute(
            select(Account).where(
                Account.user_id == current_user.id, Account.is_archived.is_(False)
            )
        )
    ).scalars().all()

    total_balance = Decimal("0.00")
    unconverted: dict[str, Decimal] = {}
    for account in accounts:
        converted = await convert(session, account.balance, account.currency, reference_currency, today)
        if converted is None:
            unconverted[account.currency] = unconverted.get(account.currency, Decimal("0.00")) + account.balance
        else:
            total_balance += converted

    month_income = await _sum_transactions_converted(
        session, current_user.id, TransactionType.INCOME, start, end, reference_currency, today
    )
    month_expenses = await _sum_transactions_converted(
        session, current_user.id, TransactionType.EXPENSE, start, end, reference_currency, today
    )

    return DashboardSummary(
        reference_currency=reference_currency,
        month=month_label,
        total_balance=total_balance,
        month_income=month_income,
        month_expenses=month_expenses,
        unconverted_balances=[
            UnconvertedAmount(currency=currency, amount=amount)
            for currency, amount in unconverted.items()
        ],
    )


async def _sum_transactions_converted(
    session: AsyncSession,
    user_id: int,
    type_: TransactionType,
    start: date_type,
    end: date_type,
    reference_currency: str,
    as_of: date_type,
) -> Decimal:
    stmt = select(Transaction.amount, Transaction.currency).where(
        Transaction.user_id == user_id,
        Transaction.type == type_,
        Transaction.date >= start,
        Transaction.date <= end,
        Transaction.id.not_in(_statement_payment_transaction_ids(user_id)),
    )
    rows = (await session.execute(stmt)).all()

    total = Decimal("0.00")
    for amount, currency in rows:
        converted = await convert(session, amount, currency, reference_currency, as_of)
        if converted is not None:
            total += converted
    return total


@router.get("/spending-by-category", response_model=list[CategorySpending])
async def get_spending_by_category(
    month: str | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CategorySpending]:
    reference_currency = get_settings().default_currency
    start, end, _ = _month_bounds(month)
    today = date_type.today()

    stmt = (
        select(
            Transaction.amount,
            Transaction.currency,
            Transaction.category_id,
            Category.name,
            Category.icon,
        )
        .join(Category, Category.id == Transaction.category_id, isouter=True)
        .where(
            Transaction.user_id == current_user.id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.date >= start,
            Transaction.date <= end,
            Transaction.id.not_in(_statement_payment_transaction_ids(current_user.id)),
        )
    )
    rows = (await session.execute(stmt)).all()

    totals: dict[int | None, CategorySpending] = {}
    for amount, currency, category_id, category_name, icon in rows:
        converted = await convert(session, amount, currency, reference_currency, today)
        if converted is None:
            continue
        if category_id not in totals:
            totals[category_id] = CategorySpending(
                category_id=category_id,
                category_name=category_name or "Sin categoría",
                icon=icon,
                total=Decimal("0.00"),
            )
        totals[category_id].total += converted

    return sorted(totals.values(), key=lambda entry: entry.total, reverse=True)


@router.get("/cash-flow-projection", response_model=CashFlowProjection)
async def get_cash_flow_projection(
    months: int = 6,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CashFlowProjection:
    if not 1 <= months <= 24:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="months debe estar entre 1 y 24"
        )
    reference_currency = get_settings().default_currency
    today = date_type.today()

    range_start = date_type(today.year, today.month, 1)
    end_year, end_month = today.year, today.month + months - 1
    end_year += (end_month - 1) // 12
    end_month = (end_month - 1) % 12 + 1
    range_end = date_type(end_year, end_month, calendar.monthrange(end_year, end_month)[1])

    statements = (
        await session.execute(
            select(CardStatement).where(
                CardStatement.user_id == current_user.id,
                CardStatement.status != StatementStatus.PAID,
                CardStatement.payment_due_date >= range_start,
                CardStatement.payment_due_date <= range_end,
            )
        )
    ).scalars().all()

    monthly_totals: dict[str, Decimal] = {}
    for statement in statements:
        total, _ = await compute_statement_totals(session, statement)
        if total <= 0:
            continue
        card = await session.get(Card, statement.card_id)
        account = await session.get(Account, card.account_id)
        converted = await convert(session, total, account.currency, reference_currency, today)
        if converted is None:
            continue
        key = f"{statement.payment_due_date.year:04d}-{statement.payment_due_date.month:02d}"
        monthly_totals[key] = monthly_totals.get(key, Decimal("0.00")) + converted

    projection: list[CashFlowMonth] = []
    year, month_num = today.year, today.month
    for _ in range(months):
        key = f"{year:04d}-{month_num:02d}"
        projection.append(
            CashFlowMonth(month=key, committed_amount=monthly_totals.get(key, Decimal("0.00")))
        )
        month_num += 1
        if month_num > 12:
            month_num = 1
            year += 1

    return CashFlowProjection(reference_currency=reference_currency, projection=projection)
