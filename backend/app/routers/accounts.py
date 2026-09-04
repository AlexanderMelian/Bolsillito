from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Account, Card, Transaction
from app.schemas.accounts import AccountCreate, AccountRead, AccountUpdate

router = APIRouter(prefix="/accounts", tags=["accounts"])


async def _get_account_or_404(account_id: int, session: AsyncSession) -> Account:
    account = await session.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    return account


@router.get("", response_model=list[AccountRead])
async def list_accounts(
    include_archived: bool = False, session: AsyncSession = Depends(get_session)
) -> list[Account]:
    stmt = select(Account).order_by(Account.name)
    if not include_archived:
        stmt = stmt.where(Account.is_archived.is_(False))
    return list((await session.execute(stmt)).scalars().all())


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate, session: AsyncSession = Depends(get_session)
) -> Account:
    account = Account(**payload.model_dump())
    session.add(account)
    await session.commit()
    await session.refresh(account)
    return account


@router.get("/{account_id}", response_model=AccountRead)
async def get_account(account_id: int, session: AsyncSession = Depends(get_session)) -> Account:
    return await _get_account_or_404(account_id, session)


@router.patch("/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: int, payload: AccountUpdate, session: AsyncSession = Depends(get_session)
) -> Account:
    account = await _get_account_or_404(account_id, session)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(account, field, value)
    await session.commit()
    await session.refresh(account)
    return account


@router.delete("/{account_id}", response_model=AccountRead)
async def delete_account(account_id: int, session: AsyncSession = Depends(get_session)) -> Account:
    """Borra la cuenta. Si tiene tarjetas o movimientos asociados, en vez de borrarla la
    archiva (`is_archived=true`) para no perder el historial -- ver docs/api-spec.md."""
    account = await _get_account_or_404(account_id, session)

    has_cards = (
        await session.execute(select(Card.id).where(Card.account_id == account_id).limit(1))
    ).first() is not None
    has_transactions = (
        await session.execute(
            select(Transaction.id)
            .where(
                (Transaction.account_id == account_id)
                | (Transaction.destination_account_id == account_id)
            )
            .limit(1)
        )
    ).first() is not None

    if has_cards or has_transactions:
        account.is_archived = True
        await session.commit()
        await session.refresh(account)
        return account

    await session.delete(account)
    await session.commit()
    return account
