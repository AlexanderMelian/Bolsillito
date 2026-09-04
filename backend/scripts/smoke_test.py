"""Prueba de humo manual de Fase 1: valida que el modelo, la migración y el algoritmo de
cuotas funcionan juntos contra una base Postgres real. No es parte del test suite (eso vive en
backend/tests/); se corre a mano con `python scripts/smoke_test.py`.
"""

import asyncio
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.services.billing_cycle import build_installment_amounts, build_installment_closing_dates
from app.database import async_session_factory
from app.models import (
    Account, AccountType, Card, CardStatement, CardType, InstallmentItem,
    InstallmentPlan, Transaction, TransactionType,
)


async def main() -> None:
    async with async_session_factory() as session:
        account = Account(name="Cuenta Sueldo", type=AccountType.BANK, currency="ARS")
        session.add(account)
        await session.flush()

        card = Card(
            account_id=account.id,
            name="Visa Gold",
            type=CardType.CREDIT,
            credit_limit=Decimal("500000.00"),
            closing_day=15,
            payment_day=25,
        )
        session.add(card)
        await session.flush()

        purchase_date = date(2026, 3, 14)
        total_amount = Decimal("300000.00")
        total_installments = 3

        plan = InstallmentPlan(
            card_id=card.id,
            description="Notebook",
            purchase_date=purchase_date,
            total_amount=total_amount,
            total_installments=total_installments,
        )
        session.add(plan)
        await session.flush()

        amounts = build_installment_amounts(total_amount, total_installments)
        closing_dates = build_installment_closing_dates(
            purchase_date, card.closing_day, total_installments
        )

        for number, (amount, closing) in enumerate(zip(amounts, closing_dates), start=1):
            statement = (
                await session.execute(
                    select(CardStatement).where(
                        CardStatement.card_id == card.id,
                        CardStatement.closing_date == closing,
                    )
                )
            ).scalar_one_or_none()
            if statement is None:
                statement = CardStatement(
                    card_id=card.id,
                    closing_date=closing,
                    payment_due_date=closing.replace(day=25),
                )
                session.add(statement)
                await session.flush()
            session.add(
                InstallmentItem(
                    plan_id=plan.id, statement_id=statement.id, number=number, amount=amount
                )
            )

        await session.commit()

        items = (
            await session.execute(
                select(InstallmentItem, CardStatement)
                .join(CardStatement, InstallmentItem.statement_id == CardStatement.id)
                .where(InstallmentItem.plan_id == plan.id)
                .order_by(InstallmentItem.number)
            )
        ).all()

        print("Compra en cuotas generada correctamente:")
        for item, statement in items:
            print(
                f"  cuota {item.number}/{total_installments}: ${item.amount} "
                f"-> resumen que cierra {statement.closing_date} "
                f"(vence {statement.payment_due_date})"
            )
        assert sum(item.amount for item, _ in items) == total_amount, "la suma no cierra"
        print("Suma de cuotas == monto total: OK")

        try:
            session.add(
                Transaction(
                    type=TransactionType.TRANSFER,
                    account_id=account.id,
                    destination_account_id=account.id,  # inválido: origen == destino
                    amount=Decimal("100.00"),
                    date=date(2026, 3, 14),
                )
            )
            await session.commit()
            print("ERROR: se esperaba que la constraint ck_transfer_needs_destination fallara")
        except IntegrityError:
            await session.rollback()
            print("Constraint ck_transfer_needs_destination bloqueó la transferencia inválida: OK")


if __name__ == "__main__":
    asyncio.run(main())
