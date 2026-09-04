from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Card
from app.schemas.cards import CardCreate, CardRead, CardUpdate, _validate_credit_card_cycle

router = APIRouter(prefix="/cards", tags=["cards"])


async def _get_card_or_404(card_id: int, session: AsyncSession) -> Card:
    card = await session.get(Card, card_id)
    if card is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tarjeta no encontrada")
    return card


@router.get("", response_model=list[CardRead])
async def list_cards(
    account_id: int | None = None, session: AsyncSession = Depends(get_session)
) -> list[Card]:
    stmt = select(Card).order_by(Card.name)
    if account_id is not None:
        stmt = stmt.where(Card.account_id == account_id)
    return list((await session.execute(stmt)).scalars().all())


@router.post("", response_model=CardRead, status_code=status.HTTP_201_CREATED)
async def create_card(payload: CardCreate, session: AsyncSession = Depends(get_session)) -> Card:
    card = Card(**payload.model_dump())
    session.add(card)
    await session.commit()
    await session.refresh(card)
    return card


@router.get("/{card_id}", response_model=CardRead)
async def get_card(card_id: int, session: AsyncSession = Depends(get_session)) -> Card:
    return await _get_card_or_404(card_id, session)


@router.patch("/{card_id}", response_model=CardRead)
async def update_card(
    card_id: int, payload: CardUpdate, session: AsyncSession = Depends(get_session)
) -> Card:
    card = await _get_card_or_404(card_id, session)
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
async def delete_card(card_id: int, session: AsyncSession = Depends(get_session)) -> None:
    """Borra la tarjeta. Si tiene movimientos o compras en cuotas asociadas, la FK (sin
    ON DELETE CASCADE a propósito) hace que Postgres rechace el borrado; el handler global de
    IntegrityError en app.main lo traduce a 409."""
    card = await _get_card_or_404(card_id, session)
    await session.delete(card)
    await session.commit()
