from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models import Account, Category, RecurringExpense, TransactionType, User
from app.schemas.recurring_expenses import (
    RecurringExpenseCreate, RecurringExpenseRead, RecurringExpenseSyncResult,
    RecurringExpenseUpdate,
)
from app.services.auth import get_current_user
from app.services.recurring_expenses import sync_recurring_expenses

router = APIRouter(prefix="/recurring-expenses", tags=["recurring-expenses"])


async def _get_expense_or_404(
    expense_id: int, user: User, session: AsyncSession
) -> RecurringExpense:
    expense = (
        await session.execute(
            select(RecurringExpense).where(
                RecurringExpense.id == expense_id, RecurringExpense.user_id == user.id
            )
        )
    ).scalar_one_or_none()
    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Gasto fijo no encontrado"
        )
    return expense


async def _get_account_or_404(account_id: int, user: User, session: AsyncSession) -> Account:
    account = (
        await session.execute(
            select(Account).where(Account.id == account_id, Account.user_id == user.id)
        )
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cuenta no encontrada")
    return account


async def _check_category(category_id: int, user: User, session: AsyncSession) -> None:
    category = (
        await session.execute(
            select(Category).where(Category.id == category_id, Category.user_id == user.id)
        )
    ).scalar_one_or_none()
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Categoría no encontrada"
        )
    if category.kind != TransactionType.EXPENSE:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="La categoría debe ser de tipo 'expense'",
        )


@router.get("", response_model=list[RecurringExpenseRead])
async def list_recurring_expenses(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[RecurringExpense]:
    stmt = (
        select(RecurringExpense)
        .where(RecurringExpense.user_id == current_user.id)
        .order_by(RecurringExpense.day_of_month)
    )
    return list((await session.execute(stmt)).scalars().all())


@router.post("", response_model=RecurringExpenseRead, status_code=status.HTTP_201_CREATED)
async def create_recurring_expense(
    payload: RecurringExpenseCreate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RecurringExpense:
    currency = payload.currency
    if payload.account_id is not None:
        account = await _get_account_or_404(payload.account_id, current_user, session)
        currency = payload.currency or account.currency
        if payload.currency is not None and payload.currency != account.currency:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="La moneda del gasto fijo debe coincidir con la de la cuenta",
            )
    if payload.category_id is not None:
        await _check_category(payload.category_id, current_user, session)

    expense = RecurringExpense(
        user_id=current_user.id,
        account_id=payload.account_id,
        category_id=payload.category_id,
        description=payload.description,
        amount=payload.amount,
        currency=currency or "ARS",
        day_of_month=payload.day_of_month,
        start_date=payload.start_date,
    )
    session.add(expense)
    await session.commit()
    await session.refresh(expense)
    return expense


@router.patch("/{expense_id}", response_model=RecurringExpenseRead)
async def update_recurring_expense(
    expense_id: int,
    payload: RecurringExpenseUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RecurringExpense:
    expense = await _get_expense_or_404(expense_id, current_user, session)

    updates = payload.model_dump(exclude_unset=True)
    if "account_id" in updates and updates["account_id"] is not None:
        await _get_account_or_404(updates["account_id"], current_user, session)
    if "category_id" in updates and updates["category_id"] is not None:
        await _check_category(updates["category_id"], current_user, session)

    for field, value in updates.items():
        setattr(expense, field, value)

    await session.commit()
    await session.refresh(expense)
    return expense


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring_expense(
    expense_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> None:
    """No borra las transacciones ya generadas -- son gasto real ya aplicado al saldo; el
    ON DELETE SET NULL de transactions.recurring_expense_id las deja como historial suelto."""
    expense = await _get_expense_or_404(expense_id, current_user, session)
    await session.delete(expense)
    await session.commit()


@router.post("/sync", response_model=RecurringExpenseSyncResult)
async def sync_recurring_expenses_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> RecurringExpenseSyncResult:
    generated = await sync_recurring_expenses(session, current_user)
    return RecurringExpenseSyncResult(generated_count=len(generated))
