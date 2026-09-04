from datetime import date as date_

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Account, Card, CardType, Category, Transaction, TransactionType, User
from app.schemas.transactions import TransactionCreate, TransactionRead, TransactionUpdate
from app.services.auth import get_current_user
from app.services.balances import apply_transaction_balance_effect
from app.services.billing_cycle import get_statement_closing_date
from app.services.card_statements import get_or_create_statement

router = APIRouter(prefix="/transactions", tags=["transactions"])


async def _get_transaction_or_404(
    transaction_id: int, user: User, session: AsyncSession
) -> Transaction:
    transaction = (
        await session.execute(
            select(Transaction).where(
                Transaction.id == transaction_id, Transaction.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Movimiento no encontrado"
        )
    return transaction


async def _validate_and_resolve(
    payload: TransactionCreate, user: User, session: AsyncSession
) -> tuple[Account, Card | None]:
    account = (
        await session.execute(
            select(Account).where(Account.id == payload.account_id, Account.user_id == user.id)
        )
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")

    card: Card | None = None
    if payload.card_id is not None:
        card = (
            await session.execute(
                select(Card).where(Card.id == payload.card_id, Card.user_id == user.id)
            )
        ).scalar_one_or_none()
        if card is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarjeta no encontrada")
        if card.account_id != payload.account_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="La tarjeta no pertenece a la cuenta indicada",
            )

    if payload.type == TransactionType.TRANSFER:
        destination = (
            await session.execute(
                select(Account).where(
                    Account.id == payload.destination_account_id, Account.user_id == user.id
                )
            )
        ).scalar_one_or_none()
        if destination is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta de destino no encontrada"
            )
        if destination.currency != account.currency:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="No se puede transferir entre cuentas de distinta moneda",
            )

    if payload.category_id is not None:
        category = (
            await session.execute(
                select(Category).where(
                    Category.id == payload.category_id, Category.user_id == user.id
                )
            )
        ).scalar_one_or_none()
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada"
            )
        if category.kind != payload.type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"La categoría es de tipo '{category.kind.value}', no '{payload.type.value}'",
            )

    if payload.currency is not None and payload.currency != account.currency:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La moneda del movimiento debe coincidir con la de la cuenta",
        )

    return account, card


@router.get("", response_model=list[TransactionRead])
async def list_transactions(
    account_id: int | None = None,
    category_id: int | None = None,
    type: TransactionType | None = None,
    date_from: date_ | None = None,
    date_to: date_ | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Transaction]:
    stmt = (
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.date.desc(), Transaction.id.desc())
    )
    if account_id is not None:
        stmt = stmt.where(
            (Transaction.account_id == account_id)
            | (Transaction.destination_account_id == account_id)
        )
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    if type is not None:
        stmt = stmt.where(Transaction.type == type)
    if date_from is not None:
        stmt = stmt.where(Transaction.date >= date_from)
    if date_to is not None:
        stmt = stmt.where(Transaction.date <= date_to)
    return list((await session.execute(stmt)).scalars().all())


@router.post("", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Transaction:
    account, card = await _validate_and_resolve(payload, current_user, session)

    data = payload.model_dump()
    data["currency"] = payload.currency or account.currency
    transaction = Transaction(**data, user_id=current_user.id)
    session.add(transaction)
    await session.flush()

    # Un gasto de pago único con tarjeta de crédito no genera InstallmentItem (eso es solo
    # para /installment-plans), pero igual necesita un CardStatement para el ciclo al que
    # pertenece -- si no, nunca aparecería en GET /cards/{id}/statements ni se podría pagar.
    if card is not None and card.type == CardType.CREDIT:
        closing_date = get_statement_closing_date(transaction.date, card.closing_day)
        await get_or_create_statement(session, card, closing_date)

    await apply_transaction_balance_effect(session, transaction, card)

    await session.commit()
    await session.refresh(transaction)
    return transaction


@router.get("/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Transaction:
    return await _get_transaction_or_404(transaction_id, current_user, session)


@router.patch("/{transaction_id}", response_model=TransactionRead)
async def update_transaction(
    transaction_id: int,
    payload: TransactionUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Transaction:
    transaction = await _get_transaction_or_404(transaction_id, current_user, session)

    updates = payload.model_dump(exclude_unset=True)
    if "category_id" in updates and updates["category_id"] is not None:
        category = (
            await session.execute(
                select(Category).where(
                    Category.id == updates["category_id"], Category.user_id == current_user.id
                )
            )
        ).scalar_one_or_none()
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada"
            )
        if category.kind != transaction.type:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"La categoría es de tipo '{category.kind.value}', no '{transaction.type.value}'",
            )
    for field, value in updates.items():
        setattr(transaction, field, value)

    await session.commit()
    await session.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Revierte el efecto sobre el saldo antes de borrar. Los movimientos que registran una
    compra en cuotas (`installment_plan_id` no nulo) no se pueden borrar directamente -- hay
    que borrar el plan de cuotas (`DELETE /installment-plans/{id}`), que se encarga de todo."""
    transaction = await _get_transaction_or_404(transaction_id, current_user, session)
    if transaction.installment_plan_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Este movimiento es el registro de una compra en cuotas. "
                "Borrá el plan de cuotas (DELETE /installment-plans/{id}) en su lugar."
            ),
        )

    card = await session.get(Card, transaction.card_id) if transaction.card_id else None
    await apply_transaction_balance_effect(session, transaction, card, sign=-1)

    await session.delete(transaction)
    await session.commit()
