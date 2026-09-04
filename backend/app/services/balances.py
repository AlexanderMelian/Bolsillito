"""Efecto de las transacciones sobre el saldo de las cuentas.

Regla de negocio confirmada (ver agents.md): un gasto con tarjeta de crédito NO afecta el saldo
de la cuenta en el momento de la compra -- se descuenta del cupo, no del banco. El saldo se
ajusta recién cuando se paga el resumen (ver services/card_statements.py). Todo lo demás
(ingreso, gasto en efectivo/débito, transferencia) sí afecta el saldo al momento del movimiento.
"""

from decimal import Decimal

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Account, Card, CardType, Transaction, TransactionType


async def adjust_balance(session: AsyncSession, account_id: int, delta: Decimal) -> None:
    """Incrementa el saldo con una sentencia SQL atómica (`balance = balance + delta`) en vez
    de leer y reescribir en Python, para no perder incrementos concurrentes."""
    await session.execute(
        update(Account).where(Account.id == account_id).values(balance=Account.balance + delta)
    )


async def apply_transaction_balance_effect(
    session: AsyncSession, transaction: Transaction, card: Card | None, *, sign: int = 1
) -> None:
    """Aplica (sign=1) o revierte (sign=-1) el efecto de `transaction` sobre el/los saldos."""
    if transaction.type == TransactionType.TRANSFER:
        await adjust_balance(session, transaction.account_id, -transaction.amount * sign)
        await adjust_balance(
            session, transaction.destination_account_id, transaction.amount * sign
        )
        return

    if card is not None and card.type == CardType.CREDIT:
        return  # compra a crédito: no toca el saldo hasta que se paga el resumen

    delta = transaction.amount if transaction.type == TransactionType.INCOME else -transaction.amount
    await adjust_balance(session, transaction.account_id, delta * sign)
