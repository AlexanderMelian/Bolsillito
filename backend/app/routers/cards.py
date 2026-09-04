from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Account, Card, CardStatement, User
from app.schemas.card_statements import CardStatementRead, StatementPaymentCreate
from app.schemas.cards import CardCreate, CardRead, CardUpdate, _validate_credit_card_cycle
from app.services.auth import get_current_user
from app.services.card_statements import compute_statement_totals, pay_statement

router = APIRouter(prefix="/cards", tags=["cards"])


async def _get_card_or_404(card_id: int, user: User, session: AsyncSession) -> Card:
    card = (
        await session.execute(select(Card).where(Card.id == card_id, Card.user_id == user.id))
    ).scalar_one_or_none()
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarjeta no encontrada")
    return card


async def _get_owned_account_or_404(account_id: int, user: User, session: AsyncSession) -> Account:
    account = (
        await session.execute(
            select(Account).where(Account.id == account_id, Account.user_id == user.id)
        )
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    return account


@router.get("", response_model=list[CardRead])
async def list_cards(
    account_id: int | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[Card]:
    stmt = select(Card).where(Card.user_id == current_user.id).order_by(Card.name)
    if account_id is not None:
        stmt = stmt.where(Card.account_id == account_id)
    return list((await session.execute(stmt)).scalars().all())


@router.post("", response_model=CardRead, status_code=status.HTTP_201_CREATED)
async def create_card(
    payload: CardCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Card:
    await _get_owned_account_or_404(payload.account_id, current_user, session)
    if payload.payment_account_id is not None:
        await _get_owned_account_or_404(payload.payment_account_id, current_user, session)

    card = Card(**payload.model_dump(), user_id=current_user.id)
    session.add(card)
    await session.commit()
    await session.refresh(card)
    return card


@router.get("/{card_id}", response_model=CardRead)
async def get_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Card:
    return await _get_card_or_404(card_id, current_user, session)


@router.patch("/{card_id}", response_model=CardRead)
async def update_card(
    card_id: int,
    payload: CardUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Card:
    card = await _get_card_or_404(card_id, current_user, session)
    if payload.payment_account_id is not None:
        await _get_owned_account_or_404(payload.payment_account_id, current_user, session)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(card, field, value)

    # CardUpdate no puede validar esto solo (es un patch parcial): se revalida el estado
    # combinado resultante contra la misma regla que aplica CardCreate.
    try:
        _validate_credit_card_cycle(card.type, card.closing_day, card.payment_day)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
        ) from exc

    await session.commit()
    await session.refresh(card)
    return card


@router.delete("/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(
    card_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Borra la tarjeta. Si tiene movimientos o compras en cuotas asociadas, la FK (sin
    ON DELETE CASCADE a propósito) hace que Postgres rechace el borrado; el handler global de
    IntegrityError en app.main lo traduce a 409."""
    card = await _get_card_or_404(card_id, current_user, session)
    await session.delete(card)
    await session.commit()


async def _statement_read(session: AsyncSession, statement: CardStatement) -> CardStatementRead:
    total_amount, status_ = await compute_statement_totals(session, statement)
    return CardStatementRead(
        id=statement.id,
        card_id=statement.card_id,
        closing_date=statement.closing_date,
        payment_due_date=statement.payment_due_date,
        status=status_,
        total_amount=total_amount,
        payment_transaction_id=statement.payment_transaction_id,
    )


@router.get("/{card_id}/statements", response_model=list[CardStatementRead])
async def list_card_statements(
    card_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CardStatementRead]:
    await _get_card_or_404(card_id, current_user, session)
    statements = (
        await session.execute(
            select(CardStatement)
            .where(CardStatement.card_id == card_id)
            .order_by(CardStatement.closing_date)
        )
    ).scalars().all()
    return [await _statement_read(session, statement) for statement in statements]


@router.post("/{card_id}/statements/{statement_id}/pay", response_model=CardStatementRead)
async def pay_card_statement(
    card_id: int,
    statement_id: int,
    payload: StatementPaymentCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CardStatementRead:
    card = await _get_card_or_404(card_id, current_user, session)
    statement = await session.get(CardStatement, statement_id)
    if statement is None or statement.card_id != card_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resumen no encontrado")
    if statement.payment_transaction_id is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Este resumen ya está pagado")

    total_amount, _ = await compute_statement_totals(session, statement)
    if total_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="El resumen no tiene saldo pendiente"
        )

    await pay_statement(session, card, statement, payload.payment_date)
    await session.commit()
    await session.refresh(statement)
    return await _statement_read(session, statement)
