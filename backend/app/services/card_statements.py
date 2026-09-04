"""Ciclos de facturación: alta de cuotas y cálculo de resúmenes.

El `total_amount` y el `status` de un `CardStatement` se calculan siempre en el momento de la
consulta (sumando `InstallmentItem` + gastos de pago único del período) en vez de mantenerse
escritos de forma incremental en la fila -- evita que la columna quede desincronizada si se
borra o edita un gasto. La columna `total_amount` en la tabla solo se persiste como registro
histórico al momento de pagar (ver `pay_statement`).
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Card, CardStatement, InstallmentItem, StatementStatus, Transaction, TransactionType
from app.services.balances import adjust_balance
from app.services.billing_cycle import get_payment_due_date


async def get_or_create_statement(session: AsyncSession, card: Card, closing_date: date) -> CardStatement:
    statement = (
        await session.execute(
            select(CardStatement).where(
                CardStatement.card_id == card.id, CardStatement.closing_date == closing_date
            )
        )
    ).scalar_one_or_none()
    if statement is None:
        statement = CardStatement(
            user_id=card.user_id,
            card_id=card.id,
            closing_date=closing_date,
            payment_due_date=get_payment_due_date(closing_date, card.payment_day),
        )
        session.add(statement)
        await session.flush()
    return statement


async def _period_start(session: AsyncSession, card_id: int, closing_date: date) -> date:
    """Fecha desde la que se cuentan los gastos de pago único de este ciclo: el día siguiente
    al cierre del resumen anterior de la misma tarjeta (o "siempre" si es el primero)."""
    previous_closing = (
        await session.execute(
            select(CardStatement.closing_date)
            .where(CardStatement.card_id == card_id, CardStatement.closing_date < closing_date)
            .order_by(CardStatement.closing_date.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    return previous_closing + timedelta(days=1) if previous_closing else date.min


async def compute_statement_totals(
    session: AsyncSession, statement: CardStatement
) -> tuple[Decimal, StatementStatus]:
    if statement.payment_transaction_id is not None:
        return statement.total_amount, StatementStatus.PAID

    installments_total = (
        await session.execute(
            select(func.coalesce(func.sum(InstallmentItem.amount), Decimal("0.00"))).where(
                InstallmentItem.statement_id == statement.id
            )
        )
    ).scalar_one()

    period_start = await _period_start(session, statement.card_id, statement.closing_date)
    onetime_total = (
        await session.execute(
            select(func.coalesce(func.sum(Transaction.amount), Decimal("0.00"))).where(
                Transaction.card_id == statement.card_id,
                Transaction.installment_plan_id.is_(None),
                Transaction.type == TransactionType.EXPENSE,
                Transaction.date >= period_start,
                Transaction.date <= statement.closing_date,
            )
        )
    ).scalar_one()

    total = installments_total + onetime_total
    status = StatementStatus.CLOSED if date.today() >= statement.closing_date else StatementStatus.OPEN
    return total, status


async def pay_statement(
    session: AsyncSession, card: Card, statement: CardStatement, payment_date: date
) -> Transaction:
    total_amount, _ = await compute_statement_totals(session, statement)
    payment_account_id = card.payment_account_id or card.account_id

    payment = Transaction(
        user_id=card.user_id,
        type=TransactionType.EXPENSE,
        account_id=payment_account_id,
        amount=total_amount,
        date=payment_date,
        description=f"Pago resumen {card.name} ({statement.closing_date.isoformat()})",
    )
    session.add(payment)
    await session.flush()

    await adjust_balance(session, payment_account_id, -total_amount)

    statement.payment_transaction_id = payment.id
    statement.status = StatementStatus.PAID
    statement.total_amount = total_amount
    return payment
